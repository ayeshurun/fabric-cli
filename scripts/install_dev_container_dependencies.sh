#!/usr/bin/env bash
set -euo pipefail

# Pinned so dev container builds are reproducible. Bump deliberately.
CHANGIE_VERSION="1.26.0"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
fi

$SUDO apt-get update && $SUDO apt-get install -y \
    cmake \
    libcairo2-dev \
    pkg-config \
    python3-dev

pip3 install -r requirements-dev.txt -r requirements-docs.txt

# changie is a single Go binary. Install it straight from its GitHub release
# instead of `npm install -g changie` so the dev container does not depend on
# the npm registry (and therefore does not need Node.js at all to be usable).
install_changie() {
    local arch archive base_url tmp_dir
    case "$(uname -m)" in
        x86_64 | amd64) arch="amd64" ;;
        aarch64 | arm64) arch="arm64" ;;
        *)
            echo "changie: unsupported architecture '$(uname -m)'" >&2
            return 1
            ;;
    esac

    archive="changie_${CHANGIE_VERSION}_linux_${arch}.tar.gz"
    base_url="https://github.com/miniscruff/changie/releases/download/v${CHANGIE_VERSION}"
    tmp_dir="$(mktemp -d)"

    curl -fsSL --retry 3 --retry-delay 2 -o "${tmp_dir}/${archive}" "${base_url}/${archive}"
    curl -fsSL --retry 3 --retry-delay 2 -o "${tmp_dir}/checksums.txt" "${base_url}/checksums.txt"

    # Exact filename match, so a substring collision cannot select the wrong digest.
    awk -v file="$archive" '$2 == file' "${tmp_dir}/checksums.txt" > "${tmp_dir}/changie.sha256"
    if [ ! -s "${tmp_dir}/changie.sha256" ]; then
        echo "changie: no checksum published for ${archive}" >&2
        rm -rf "$tmp_dir"
        return 1
    fi

    (cd "$tmp_dir" && sha256sum --check --strict changie.sha256)

    tar -xzf "${tmp_dir}/${archive}" -C "$tmp_dir" changie
    $SUDO install -m 0755 "${tmp_dir}/changie" /usr/local/bin/changie
    rm -rf "$tmp_dir"
}

install_changie
changie --version
