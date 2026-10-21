#!/usr/bin/env bash
set -Eeuo pipefail

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == Linux ]] || fail 'Run this installer on Ubuntu Linux.'
[[ "$(id -u)" -eq 0 ]] || fail 'Run with sudo: sudo bash /path/to/ubuntu-one-command.sh'
[[ -r /etc/os-release ]] || fail 'Cannot identify this Linux distribution.'
# shellcheck disable=SC1091
. /etc/os-release
[[ "${ID:-}" == ubuntu && "${VERSION_ID:-}" =~ ^(22\.04|24\.04|26\.04)$ ]] || fail 'This one-command installer supports Ubuntu 22.04, 24.04, or 26.04 LTS.'

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates curl git gnupg openssl python3

configure_docker_repository() {
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
  [[ -n "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}" ]] || fail 'Ubuntu release codename is missing.'
  apt-get update -qq
}

if ! command -v docker >/dev/null 2>&1; then
  configure_docker_repository
  DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
elif ! docker compose version >/dev/null 2>&1; then
  configure_docker_repository
  DEBIAN_FRONTEND=noninteractive apt-get install -y docker-compose-plugin
fi

command -v docker >/dev/null 2>&1 || fail 'Docker Engine installation failed.'
docker compose version >/dev/null 2>&1 || fail 'Docker Compose v2 is required. Existing Docker installation was left unchanged.'
systemctl enable --now docker

REPO_URL="${NCET_REPO_URL:-https://github.com/paladuguganeshnaidu/ncet.git}"
INSTALL_DIR="${NCET_INSTALL_DIR:-/opt/ncet-verifyflow}"
if [[ -e "$INSTALL_DIR" ]]; then
  [[ -d "$INSTALL_DIR/.git" ]] || fail "$INSTALL_DIR exists and is not a Git checkout; move it aside before installing."
  [[ "$(git -C "$INSTALL_DIR" remote get-url origin)" == "$REPO_URL" ]] || fail "$INSTALL_DIR points to a different repository; refusing to replace it."
  git -C "$INSTALL_DIR" pull --ff-only origin main
else
  git clone --depth 1 --branch main "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
exec bash deploy/ubuntu-install.sh
