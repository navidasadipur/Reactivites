#!/bin/bash
# A real HTTP response, not just an open port. Database readiness is separate.
set -eu
exec 3<>/dev/tcp/127.0.0.1/8080
printf 'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' >&3
IFS= read -r status <&3
exec 3>&-
case "$status" in
  HTTP/1.0\ 200*|HTTP/1.1\ 200*) exit 0 ;;
  *) exit 1 ;;
esac
