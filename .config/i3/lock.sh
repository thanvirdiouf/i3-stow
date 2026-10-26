#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Picom supplies the spinning ball; without it this is a normal opaque lock.
# Keep this color synchronized with BACKGROUND in picom/lockscreen.frag.
# exec + --nofork preserves xss-lock's sleep descriptor until i3lock is ready.
config_dir=$(CDPATH= cd -- "$(dirname -- "$(readlink -f -- "$0")")" && pwd)
image="$config_dir/lockscreen-image.png"
if [ -r "$image" ]; then
    exec i3lock --nofork --color=1e1e2e --image="$image"
fi
exec i3lock --nofork --color=1e1e2e
