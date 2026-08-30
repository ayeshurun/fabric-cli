#!/usr/bin/env bash
set -euo pipefail

# Pinned changie release. To upgrade, bump CHANGIE_VERSION and refresh both digests from
# https://github.com/miniscruff/changie/releases/download/v<CHANGIE_VERSION>/checksums.txt
CHANGIE_VERSION="1.26.0"
CHANGIE_SHA256_AMD64="eab168c8287a6e91912e1c02e5260911232d945bfd3c89d8a0e1ace6bb7b6161"
CHANGIE_SHA256_ARM64="ec1e542014b5134f1cf86b3a12e86d566ab5ec9bd3901bf66f42a09cd9865b6e"

# postCreateCommand runs as the non-root "vscode" user, which has passwordless sudo.
#
# The base image ships an apt source for yarn whose signing key is no longer valid, which makes
# every "apt-get update" in this container exit 100. Nothing here uses yarn or Node.js, so drop
# the broken source rather than masking the failure.
sudo rm -f /etc/apt/sources.list.d/yarn.list

sudo apt-get update
sudo apt-get install -y \
    cmake \
    libcairo2-dev \
    pkg-config \
    python3-dev

pip3 install -r requirements-dev.txt -r requirements-docs.txt

# changie ships as a standalone Go binary, so we install it straight from the GitHub release
# instead of via `npm install -g changie`. That keeps the dev container free of Node.js and of
# the public npm registry, which is unreachable on networks that enforce an internal feed proxy.
install_changie() {
    local arch expected tarball url tmp status=0

    arch="$(dpkg --print-architecture)"
    case "$arch" in
        amd64) expected="$CHANGIE_SHA256_AMD64" ;;
        arm64) expected="$CHANGIE_SHA256_ARM64" ;;
        *)
            echo "No changie release available for architecture '$arch'." >&2
            return 1
            ;;
    esac

    tarball="changie_${CHANGIE_VERSION}_linux_${arch}.tar.gz"
    url="https://github.com/miniscruff/changie/releases/download/v${CHANGIE_VERSION}/${tarball}"
    tmp="$(mktemp -d)"

    if curl -fsSL --retry 3 --retry-connrefused -o "${tmp}/${tarball}" "$url" &&
        echo "${expected}  ${tmp}/${tarball}" | sha256sum --check --status &&
        tar -xzf "${tmp}/${tarball}" -C "$tmp" changie &&
        sudo install -m 0755 "${tmp}/changie" /usr/local/bin/changie; then
        status=0
    else
        status=1
    fi

    rm -rf "$tmp"
    return "$status"
}

if install_changie; then
    echo "Installed changie ${CHANGIE_VERSION} to /usr/local/bin/changie."
else
    cat >&2 <<'EOF'

WARNING: changie could not be installed.
The dev container is still usable, but 'changie new' will not work. Every pull request needs
a changelog entry, so either retry the install manually:

  bash scripts/install_dev_container_dependencies.sh

or hand-write a YAML entry under .changes/unreleased/ (see CONTRIBUTING.md).

EOF
fi
