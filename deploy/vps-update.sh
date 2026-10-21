#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${DEPLOY_PATH_B64:-}" =~ ^[A-Za-z0-9+/=]+$ ]] || { echo 'Invalid deployment path parameter.' >&2; exit 2; }
DEPLOY_PATH="$(printf '%s' "$DEPLOY_PATH_B64" | base64 -d)"
[[ "$DEPLOY_PATH" == /* && -d "$DEPLOY_PATH/.git" ]] || { echo 'Deployment directory must be an absolute path containing the cloned Git repository.' >&2; exit 2; }
cd "$DEPLOY_PATH"
git pull --ff-only origin main
docker compose pull database clamav proxy
docker compose up -d --build --remove-orphans --wait --wait-timeout 900
docker compose ps
