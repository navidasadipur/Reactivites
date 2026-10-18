"""Disposable packaging rehearsal on a GitHub-hosted Linux runner only.

No production credentials, databases or SSH access are used. The uploaded report
contains no tokens, passwords or database backup; backups stay on the ephemeral VM.
"""
import datetime
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or sys.platform != "linux":
        raise SystemExit("This script is restricted to disposable GitHub Linux runners.")
    image = os.environ["REHEARSAL_IMAGE"]
    root = Path(__file__).resolve().parents[1]
    output = root / "deploy/releases"
    output.mkdir(parents=True, exist_ok=True)
    report = {"image": image, "source_revision": os.environ.get("GITHUB_SHA"),
              "public_release_ready": False, "checks": {}, "status": "running"}
    checks = report["checks"]
    token_key = secrets.token_hex(64)

    def run(*args):
        result = subprocess.run(args, cwd=root, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=180)
        if result.returncode:
            raise RuntimeError("Command failed: " + " ".join(args[:3]) + "\n" +
                               result.stdout.replace(token_key, "[redacted]"))
        return result.stdout

    def request(port, path, method="GET", data=None, token=None, expected=200):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}", method=method, headers=headers,
            data=json.dumps(data).encode() if data is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, received {status}")
        return json.loads(body) if body and body[:1] in (b"{", b"[") else body

    # Never take over containers/volumes left by a different task.
    app = "reactivities-rehearsal"
    restored = "reactivities-restore-check"
    volume = "reactivities-rehearsal-data"
    restored_volume = "reactivities-restore-check-data"
    network = "reactivities-rehearsal-net"
    for kind, names in (("container", (app, restored)),
                        ("volume", (volume, restored_volume)), ("network", (network,))):
        existing = run("docker", kind, "ls", "--format", "{{.Name}}" if kind != "container" else "{{.Names}}", *(["-a"] if kind == "container" else [])).splitlines()
        if set(names) & set(existing):
            raise SystemExit("Refusing to reuse existing rehearsal resources.")

    with tempfile.TemporaryDirectory(prefix="reactivities-rehearsal-") as temporary:
        work = Path(temporary)
        image_name, image_tag = image.rsplit(":", 1)
        env = work / "rehearsal.env"
        env.write_text(f"REACTIVITIES_IMAGE={image_name}\nREACTIVITIES_TAG={image_tag}\n"
                       f"REACTIVITIES_TOKEN_KEY={token_key}\n")
        env.chmod(0o600)
        compose = ["docker", "compose", "-p", "reactivities-rehearsal", "--env-file", str(env),
                   "-f", "deploy/compose.yml", "-f", "deploy/compose.rehearsal.yml"]
        created_restore_volume = False
        started_restore = False
        try:
            run(*compose, "config", "--quiet")
            checks["compose_valid"] = True
            run(*compose, "up", "-d", "--wait", "--wait-timeout", "120", "--no-build", "--pull", "never", "app")
            checks["http_liveness_healthy"] = True
            run("docker", "exec", app, "sh", "-c",
                'test "$(id -u)" = 10001 && test -w /app/data && test ! -e /app/appsettings.Development.json')
            checks["nonroot_writable_volume_no_development_config"] = True
            assert b"<html" in request(18080, "/").lower()
            assert b"<html" in request(18080, "/activities").lower()
            checks["spa_and_direct_route"] = True
            request(18080, "/api/account", expected=401)
            checks["anonymous_api_rejected"] = True

            suffix = uuid.uuid4().hex[:12]
            credentials = {"displayName": "Rehearsal", "username": "rehearsal" + suffix,
                           "email": suffix + "@example.invalid", "password": "Q7!" + secrets.token_hex(2) + "z"}
            user = request(18080, "/api/account/register", "POST", credentials)
            token = user["token"]
            activity_id = str(uuid.uuid4())
            activity = {"id": activity_id, "title": "Disposable deployment rehearsal",
                        "description": "Ephemeral test data", "category": "culture",
                        "date": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat(),
                        "city": "Test", "venue": "GitHub runner"}
            request(18080, "/api/activities", "POST", activity, token)
            assert request(18080, "/api/activities/" + activity_id, token=token)["id"] == activity_id
            checks["registration_and_database_write_read"] = True
            logs = run(*compose, "logs", "--no-color", "app")
            if "An error occured during migration" in logs:
                raise RuntimeError("Startup logged a migration failure.")
            checks["no_logged_migration_failure"] = True

            run(*compose, "up", "-d", "--force-recreate", "--wait", "--wait-timeout", "120", "--no-build", "--pull", "never", "app")
            login = request(18080, "/api/account/login", "POST", credentials)
            token = login["token"]
            assert request(18080, "/api/activities/" + activity_id, token=token)["id"] == activity_id
            checks["user_and_activity_survive_recreate"] = True

            # Copy a stopped database with all journal files and numeric ownership.
            run(*compose, "stop", "app")
            run("docker", "run", "--rm", "--user", "0", "--entrypoint", "tar",
                "--mount", f"type=volume,src={volume},dst=/data,readonly",
                "--mount", f"type=bind,src={work},dst=/backup", image,
                "-czf", "/backup/data.tar.gz", "-C", "/data", ".")
            run(*compose, "up", "-d", "--wait", "--wait-timeout", "120", "--no-build", "--pull", "never", "app")
            run("docker", "volume", "create", restored_volume)
            created_restore_volume = True
            run("docker", "run", "--rm", "--user", "0", "--entrypoint", "tar",
                "--mount", f"type=volume,src={restored_volume},dst=/data",
                "--mount", f"type=bind,src={work},dst=/backup,readonly", image,
                "-xzf", "/backup/data.tar.gz", "-C", "/data")
            restore_env = work / "restore.env"
            restore_env.write_text("TokenKey=" + token_key + "\nConnectionStrings__DefaultConnection=Data Source=/app/data/reactivities.db\n")
            restore_env.chmod(0o600)
            run("docker", "run", "-d", "--name", restored, "--env-file", str(restore_env),
                "-p", "127.0.0.1:18081:8080", "--mount", f"type=volume,src={restored_volume},dst=/app/data", image)
            started_restore = True
            import time
            for attempt in range(90):
                status = run("docker", "inspect", "--format", "{{.State.Health.Status}}", restored).strip()
                if status == "healthy":
                    break
                if status == "unhealthy":
                    raise RuntimeError("Restored container is unhealthy.")
                time.sleep(1)
            else:
                raise RuntimeError("Restored container health timed out.")
            restored_user = request(18081, "/api/account/login", "POST", credentials)
            assert request(18081, "/api/activities/" + activity_id, token=restored_user["token"])["id"] == activity_id
            checks["backup_restored_to_separate_volume"] = True

            # Record this deliberately deferred application defect; it is not a packaging pass.
            request(18080, "/chat/negotiate?negotiateVersion=1", "POST", expected=200)
            report["deferred"] = ["Anonymous SignalR negotiation is still allowed",
                "Production demo seeding remains enabled", "Chat client still uses localhost",
                ".NET 7 and Node 20 upgrade pending", "Cloudinary credentials not supplied",
                "Existing local SQLite data import and real release-to-release rollback not rehearsed"]
            report["image_id"] = run("docker", "image", "inspect", "--format", "{{.Id}}", image).strip()
            report["status"] = "packaging-rehearsal-passed"
        except Exception as error:
            report["status"] = "failed"
            report["error"] = str(error).replace(token_key, "[redacted]")
            raise
        finally:
            (output / "rehearsal-report.json").write_text(json.dumps(report, indent=2))
            if started_restore:
                run("docker", "rm", "-f", restored)
            if created_restore_volume:
                run("docker", "volume", "rm", restored_volume)
            # Only this preflight-checked, disposable runner project is removed.
            run(*compose, "down", "--volumes")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
