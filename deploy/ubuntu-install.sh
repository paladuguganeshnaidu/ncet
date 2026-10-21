#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == Linux ]] || fail 'Run this installer on Ubuntu or another Linux host.'
[[ "$(id -u)" -eq 0 ]] || fail 'Run with sudo: sudo bash deploy/ubuntu-install.sh'
command -v docker >/dev/null || fail 'Docker Engine is missing. Use deploy/ubuntu-one-command.sh to install prerequisites and deploy.'
docker compose version >/dev/null 2>&1 || fail 'Docker Compose v2 plugin is missing.'
command -v openssl >/dev/null || fail 'OpenSSL is missing. Install it with: apt-get install openssl'
command -v curl >/dev/null || fail 'curl is missing. Install it with: apt-get install curl'
command -v python3 >/dev/null || fail 'Python 3 is missing; it is required to validate the server IPv4 address.'
[[ -f .env ]] && fail '.env already exists. Refusing to overwrite secrets; back it up and remove it deliberately before reinstalling.'

read -r -p 'Public hostname for this site [ncet.paladuguganeshnaidu.tech]: ' PUBLIC_HOST
PUBLIC_HOST="${PUBLIC_HOST:-ncet.paladuguganeshnaidu.tech}"
[[ "$PUBLIC_HOST" =~ ^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$ ]] || fail 'Enter a hostname only, without scheme, port, or path.'

DETECTED_IPV4="$(curl -4fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
if [[ "$DETECTED_IPV4" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
  read -r -p "Server public IPv4 for your DNS A record [$DETECTED_IPV4]: " SERVER_IPV4
  SERVER_IPV4="${SERVER_IPV4:-$DETECTED_IPV4}"
else
  read -r -p 'Server public IPv4 for your DNS A record: ' SERVER_IPV4
fi
python3 - "$SERVER_IPV4" <<'PY' || fail 'Enter a valid public IPv4 address for the DNS A record.'
import ipaddress
import sys

address = ipaddress.IPv4Address(sys.argv[1])
if not address.is_global:
    raise ValueError('The address must be public and globally routable.')
PY

read -r -p 'Initial admin username [admin]: ' ADMIN_USERNAME
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
[[ "$ADMIN_USERNAME" =~ ^[a-zA-Z0-9_.@-]{3,64}$ ]] || fail 'Username must be 3-64 letters, digits, or . _ @ - characters.'
read -r -s -p 'Initial admin password (16-128 letters/digits/underscore/hyphen): ' ADMIN_PASSWORD; printf '\n'
[[ ${#ADMIN_PASSWORD} -ge 16 && ${#ADMIN_PASSWORD} -le 128 ]] || fail 'Admin password must be between 16 and 128 characters.'
[[ "$ADMIN_PASSWORD" =~ ^[a-zA-Z0-9_-]+$ ]] || fail 'Use only letters, digits, underscore, and hyphen in this password.'
read -r -s -p 'Confirm admin password: ' ADMIN_PASSWORD_CONFIRM; printf '\n'
[[ "$ADMIN_PASSWORD" == "$ADMIN_PASSWORD_CONFIRM" ]] || fail 'Passwords do not match.'

POSTGRES_PASSWORD="$(openssl rand -hex 32)"
SETTINGS_ENCRYPTION_KEY="$(openssl rand -base64 32 | tr '+/' '-_')"
umask 077
cat > .env <<EOF
APP_ENV=production
PUBLIC_HOST=${PUBLIC_HOST}
PUBLIC_ORIGIN=https://${PUBLIC_HOST}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
SETTINGS_ENCRYPTION_KEY=${SETTINGS_ENCRYPTION_KEY}
NCET_BOOTSTRAP_ADMIN_USERNAME=${ADMIN_USERNAME}
NCET_BOOTSTRAP_ADMIN_PASSWORD=${ADMIN_PASSWORD}
SCAN_MODE=clamav
CLAMAV_HOST=clamav
CLAMAV_PORT=3310
EOF
unset POSTGRES_PASSWORD SETTINGS_ENCRYPTION_KEY ADMIN_PASSWORD ADMIN_PASSWORD_CONFIRM
chmod 600 .env

docker compose config --quiet || fail 'Compose configuration validation failed; .env was created. Correct the reported issue and rerun docker compose config.'
docker compose pull database clamav proxy
docker compose up -d --build --remove-orphans --wait --wait-timeout 900

printf '\nNCET deployment is running. Container status:\n'
docker compose ps
printf '\nAdd this DNS record at your domain provider (DNS only; do not paste application secrets there):\n'
printf '  Type: A\n  Name/Host: %s\n  Value/Points to: %s\n  TTL: provider default\n' "$PUBLIC_HOST" "$SERVER_IPV4"
printf '  Optional: add an AAAA record only if this server has working public IPv6.\n'
printf '  If this hostname currently has a CNAME to Render, replace that CNAME with the A record only when you are ready to route this hostname to the VPS.\n'
printf '\nAllow inbound TCP 80 and 443 (and UDP 443 for HTTP/3) in the VPS/cloud firewall.\n'
printf 'Caddy will request HTTPS after DNS points to this server and ports 80/443 are reachable.\n'
printf '\nPrivate server variables in %s/.env (mode 600):\n' "$ROOT"
printf '  APP_ENV, PUBLIC_HOST, PUBLIC_ORIGIN, POSTGRES_PASSWORD, SETTINGS_ENCRYPTION_KEY\n'
printf '  NCET_BOOTSTRAP_ADMIN_USERNAME, NCET_BOOTSTRAP_ADMIN_PASSWORD\n'
printf '  SCAN_MODE=clamav, CLAMAV_HOST=clamav, CLAMAV_PORT=3310\n'
printf 'The database and encryption secrets were generated automatically; keep .env private and backed up.\n'
printf 'After DNS/TLS is ready, verify: https://%s/healthz\n' "$PUBLIC_HOST"
