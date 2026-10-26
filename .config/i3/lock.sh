#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# QML supplies the artwork; i3lock supplies the X11 grabs and authentication.
# Both execs preserve xss-lock's sleep descriptor until i3lock is ready.
config_dir=$(CDPATH= cd -- "$(dirname -- "$(readlink -f -- "$0")")/../quickshell" && pwd)
if command -v python3 >/dev/null 2>&1 && [ -f "$config_dir/lock-screen.py" ]; then
    exec python3 "$config_dir/lock-screen.py"
fi
exec i3lock --nofork --color=282a36
