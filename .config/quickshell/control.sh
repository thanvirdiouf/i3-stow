#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Keep explicit paths so repository previews and Stow installations both work.
# Quickshell 0.3 identifies instances by the non-canonical config path. Preserve
# the Stow symlink path used by i3 instead of resolving it to the repository.
config_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -L)
case "${1:-}" in
    launcher)
        exec rofi -show drun
        ;;
    monitor)
        if quickshell ipc --path "$config_dir/shell.qml" call desktop "$1" 2>/dev/null; then
            exit 0
        fi
        exec i3-nagbar -t warning -m 'Start Quickshell to open the system monitor.'
        ;;
    *) printf '%s\n' 'Usage: control.sh launcher|monitor' >&2; exit 2 ;;
esac
