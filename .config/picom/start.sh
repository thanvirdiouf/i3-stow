#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Use Picom from PATH, including the regular Nix profile.
set -eu
config_dir=$(CDPATH= cd -- "$(dirname -- "$(readlink -f -- "$0")")" && pwd)
compositor=$(command -v picom)
major=$("$compositor" --version | sed -n 's/^v\{0,1\}\([0-9][0-9]*\).*/\1/p' | head -n 1)
config="$config_dir/picom.conf"
case "$major" in
    '') printf '%s\n' "Cannot determine Picom version: $compositor" >&2; exit 1 ;;
    *) if [ "$major" -lt 12 ]; then config="$config_dir/legacy.conf"; fi ;;
esac
# Nix's GL libraries need the same host-driver bridge as Quickshell.
if command -v nixGL >/dev/null 2>&1; then
    exec nixGL "$compositor" --config "$config" "$@"
fi
exec "$compositor" --config "$config" "$@"
