#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail

# Prefer a distribution-managed bridge, then our small user-local extraction.
bridge=$(command -v xembedsniproxy || command -v xembed-sni-proxy || true)
if [[ -z "$bridge" ]]; then
    bridge="${XDG_DATA_HOME:-$HOME/.local/share}/quickshell/xembed-sni-proxy/xembedsniproxy"
fi
if [[ ! -x "$bridge" ]]; then
    printf '%s\n' 'Legacy tray bridge missing: run bash ~/.config/quickshell/install-tray-bridge.sh' >&2
    exit 1
fi

# A Nix Qt 6 parent can export plugin/library paths incompatible with the
# distribution's Qt 5 bridge. Keep its Qt runtime separate from Quickshell's.
exec env -u QT_PLUGIN_PATH -u QT_QPA_PLATFORM_PLUGIN_PATH \
    -u QML2_IMPORT_PATH -u QML_IMPORT_PATH -u LD_LIBRARY_PATH \
    "$bridge"
