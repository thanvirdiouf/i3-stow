#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail

# Extract only KDE's tray bridge from the configured Debian/Ubuntu repository.
# No root access, full Plasma installation, or bundled binaries in Git needed.
destination="${XDG_DATA_HOME:-$HOME/.local/share}/quickshell/xembed-sni-proxy"
temporary=$(mktemp -d)
trap 'rm -rf -- "$temporary"' EXIT

if (( $# > 1 )); then
    printf 'Usage: %s [plasma-workspace.deb]\n' "$0" >&2
    exit 2
fi
if (( $# == 1 )); then
    archive=$(realpath -- "$1")
else
    (cd "$temporary" && apt-get download plasma-workspace)
    shopt -s nullglob
    archives=("$temporary"/plasma-workspace_*.deb)
    if (( ${#archives[@]} != 1 )); then
        printf '%s\n' 'Expected one plasma-workspace package.' >&2
        exit 1
    fi
    archive=${archives[0]}
fi

dpkg-deb --extract "$archive" "$temporary/package"
binary="$temporary/package/usr/bin/xembedsniproxy"
if [[ ! -x "$binary" ]]; then
    printf '%s\n' 'This package does not contain usr/bin/xembedsniproxy.' >&2
    exit 1
fi
dependencies=$(ldd "$binary")
if [[ "$dependencies" == *'not found'* ]]; then
    printf '%s\n' "$dependencies" >&2
    printf '%s\n' 'Install the missing runtime libraries before installing the bridge.' >&2
    exit 1
fi

install -d "$destination"
install -m 755 "$binary" "$destination/xembedsniproxy"
install -m 644 "$temporary/package/usr/share/doc/plasma-workspace/copyright" "$destination/copyright"
dpkg-deb --field "$archive" Package Version Architecture > "$destination/package.txt"
printf 'Installed tray bridge at %s\n' "$destination/xembedsniproxy"
