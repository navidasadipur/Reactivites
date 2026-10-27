# Deployment baseline

This app ships as one Linux/amd64 image: the React build is served by the ASP.NET
Core API. SQLite data lives in a separate volume mounted at `/app/data`.

## Branches and checks

- `develop` is the ongoing development branch.
- Release changes go through a pull request from `develop` to `main`.
- `main` is the production source branch; the first baseline PR is reviewed before merging.
- The `Build and rehearse` check builds the image and exercises a disposable database:
  registration, protected API access, writes, recreation persistence and backup restoration.
- CI runs for develop pushes, pull requests targeting main and manual dispatches.
- This baseline does not publish images, deploy, access the live server or use production secrets.

The workflow contains build/test checks only. Public GHCR publication and roughly
30-minute server-side update checks will be added in the next CI/CD stages, after
the baseline is reviewed and the server identity has been verified.

## Configuration and persistence

`compose.yml` defines the app service, network and data volume without publishing
a host port. An existing reverse proxy can join the app network. Copy `.env.example`
to a protected server configuration file and supply a unique signing key of at least
64 UTF-8 bytes. Never commit the actual `.env`.

The variables are `REACTIVITIES_IMAGE`, `REACTIVITIES_TAG`, and
`REACTIVITIES_TOKEN_KEY`. Optional Cloudinary variables are intentionally empty for
this demo. TokenKey in the app is independent from other projects' signing keys.

`compose.rehearsal.yml` adds loopback-only access on port 18080 and separate
rehearsal container, network and volume names. `rehearse_on_runner.py` is restricted
to a disposable GitHub-hosted Linux runner and uses generated test credentials.

Secrets, database files, image archives and backups are excluded from the Docker
context. The old SQLite file is no longer tracked in new commits; existing local
copies and old Git history are preserved. Do not remove the live data volume to update code.

## Baseline limitations

This is a learning/portfolio deployment, retaining its current application behavior:

- .NET 7 and Node 20 require a separate supported-runtime upgrade.
- Demo users are seeded; shared demo credentials are not suitable for private user data.
- The client chat URL and Hub authorization still need fixes. The existing rehearsal
  records anonymous chat negotiation as a deferred defect, not a security test passed.
- Cloudinary is unconfigured, so photo upload is not a verified feature.
- HTTP liveness only checks the frontend; database readiness and fatal migration
  failure handling are planned deployment improvements.

Application fixes and AI/MCP integration follow as separate changes. The CI report
deliberately retains `public_release_ready=false` until those criteria are addressed.
