#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

# postCreateCommand runs as the container's remote user, which may be non-root.
# Route privileged steps through sudo, leaving the prefix empty when already root
# so the script behaves identically under either user. sudo resets the
# environment by default, so proxy variables are preserved explicitly for apt.
if [ "$(id -u)" -eq 0 ]; then
    sudo_cmd=()
else
    if ! command -v sudo >/dev/null 2>&1; then
        echo "Not running as root and sudo is unavailable; cannot install packages." >&2
        exit 1
    fi
    if ! sudo -n true >/dev/null 2>&1; then
        echo "sudo requires a password; expected passwordless sudo in the dev container." >&2
        exit 1
    fi
    sudo_cmd=(sudo -n --preserve-env=http_proxy,https_proxy,no_proxy)
fi

# Optional local overrides for restricted networks, e.g. pointing PIP_INDEX_URL at
# an internal mirror. The file is git-ignored so mirror URLs stay out of the repo.
# Lines are parsed as plain KEY=value data rather than sourced, so the file cannot
# run commands or clobber this script's own variables. See local.env.example.
local_env="${repo_root}/.devcontainer/local.env"
if [ -f "$local_env" ]; then
    echo "Applying local overrides from ${local_env}"
    while IFS= read -r raw_line || [ -n "$raw_line" ]; do
        line="${raw_line%$'\r'}"
        case "$line" in ''|'#'*) continue ;; esac
        case "$line" in *=*) ;; *) continue ;; esac

        key="${line%%=*}"
        value="${line#*=}"
        key="${key#"${key%%[![:space:]]*}"}"
        key="${key%"${key##*[![:space:]]}"}"
        value="${value#"${value%%[![:space:]]*}"}"
        value="${value%"${value##*[![:space:]]}"}"
        case "$value" in
            \"*\") value="${value#\"}"; value="${value%\"}" ;;
            \'*\') value="${value#\'}"; value="${value%\'}" ;;
        esac

        case "$key" in
            PIP_INDEX_URL|PIP_EXTRA_INDEX_URL|PIP_TRUSTED_HOST|\
PIP_RETRIES|PIP_TIMEOUT|CHANGIE_VERSION|\
http_proxy|https_proxy|no_proxy|HTTP_PROXY|HTTPS_PROXY|NO_PROXY)
                export "${key}=${value}"
                echo "  applied ${key}"
                ;;
            *)
                echo "  ignoring unsupported key: ${key}" >&2
                ;;
        esac
    done < "$local_env"
fi

# The base image ships a Yarn apt source whose bundled keyring predates Yarn's
# switch to an EdDSA signing key, so `apt-get update` fails verification and
# exits 100 on an otherwise healthy network. Nothing here needs Yarn, so the
# stale source is removed rather than worked around.
yarn_list="/etc/apt/sources.list.d/yarn.list"
if [ -f "$yarn_list" ]; then
    echo "Removing stale Yarn apt source (${yarn_list})"
    "${sudo_cmd[@]}" rm -f "$yarn_list"
fi

# Kept as separate statements: under `set -e` a failing left-hand side of `&&`
# does not abort the script, which previously let package installation be skipped
# silently.
"${sudo_cmd[@]}" apt-get update
"${sudo_cmd[@]}" apt-get install -y \
    cmake \
    libcairo2-dev \
    pkg-config \
    python3-dev

# Not routed through sudo: pip falls back to a --user install when site-packages
# is not writable, and sudo would discard PIP_INDEX_URL set above.
pip3 install -r "${repo_root}/requirements-dev.txt" -r "${repo_root}/requirements-docs.txt"

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

curl_opts=(
    --fail --silent --show-error --location
    --proto '=https' --proto-redir '=https'
    --retry 3 --retry-connrefused
    --connect-timeout 15 --max-time 300
)
curl "${curl_opts[@]}" -o "${changie_tmp}/${changie_archive}" "${changie_base_url}/${changie_archive}"
curl "${curl_opts[@]}" -o "${changie_tmp}/checksums.txt" "${changie_base_url}/checksums.txt"

# Require exactly one checksum line matching the archive name on field 2, so a
# truncated or unexpected checksums.txt cannot skip verification.
checksum_line="$(awk -v archive="$changie_archive" '$2 == archive' "${changie_tmp}/checksums.txt")"
match_count="$(printf '%s' "$checksum_line" | grep -c . || true)"
if [ "$match_count" -ne 1 ]; then
    echo "Expected 1 checksum entry for ${changie_archive}, found ${match_count}." >&2
    exit 1
fi
(cd "$changie_tmp" && printf '%s\n' "$checksum_line" | sha256sum -c -)

tar -xzf "${changie_tmp}/${changie_archive}" -C "$changie_tmp" changie
# /usr/local/bin is on PATH for the remote user; ~/.local/bin is not.
"${sudo_cmd[@]}" install -m 0755 "${changie_tmp}/changie" /usr/local/bin/changie
