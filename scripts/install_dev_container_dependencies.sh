#!/usr/bin/env bash
set -e

# postCreateCommand runs as the container's remote user, which may be non-root.
# Route privileged steps through sudo, leaving the prefix empty when already
# root so the script behaves identically under either user.
if [ "$(id -u)" -eq 0 ]; then
    sudo_cmd=""
else
    sudo_cmd="sudo"
fi

# Optional local overrides for restricted networks, e.g. pointing PIP_INDEX_URL at
# an internal mirror. The file is git-ignored so mirror URLs stay out of the repo.
# See .devcontainer/local.env.example.
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
local_env="${script_dir}/../.devcontainer/local.env"
if [ -f "$local_env" ]; then
    echo "Applying local overrides from ${local_env}"
    set -a
    # shellcheck disable=SC1090 # Optional file resolved at runtime.
    . "$local_env"
    set +a
fi

# shellcheck disable=SC2086 # sudo_cmd is intentionally unquoted so it expands to nothing as root.
$sudo_cmd apt-get update && $sudo_cmd apt-get install -y \
    cmake \
    libcairo2-dev \
    pkg-config \
    python3-dev

pip3 install -r requirements-dev.txt -r requirements-docs.txt

# changie ships as a standalone Go binary, so it is installed straight from the
# upstream GitHub release. This avoids pulling a full Node.js toolchain into the
# dev container solely to run `npm install -g changie`.
CHANGIE_VERSION="${CHANGIE_VERSION:-1.26.0}"

case "$(uname -m)" in
    x86_64) changie_arch="amd64" ;;
    aarch64 | arm64) changie_arch="arm64" ;;
    *) echo "Unsupported architecture for changie: $(uname -m)" >&2; exit 1 ;;
esac

changie_archive="changie_${CHANGIE_VERSION}_linux_${changie_arch}.tar.gz"
changie_base_url="https://github.com/miniscruff/changie/releases/download/v${CHANGIE_VERSION}"
changie_tmp="$(mktemp -d)"
trap 'rm -rf "$changie_tmp"' EXIT

curl -fsSL -o "${changie_tmp}/${changie_archive}" "${changie_base_url}/${changie_archive}"
curl -fsSL -o "${changie_tmp}/checksums.txt" "${changie_base_url}/checksums.txt"

# Exact filename match on field 2 keeps the checksum line unambiguous.
(cd "$changie_tmp" && awk -v archive="$changie_archive" '$2 == archive' checksums.txt | sha256sum -c -)

tar -xzf "${changie_tmp}/${changie_archive}" -C "$changie_tmp" changie
# /usr/local/bin is on PATH for the remote user; ~/.local/bin is not.
$sudo_cmd install -m 0755 "${changie_tmp}/changie" /usr/local/bin/changie
