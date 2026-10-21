#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Picom supplies the animation; without it this remains a normal opaque lock.
# exec + --nofork preserves xss-lock's XSS_SLEEP_LOCK_FD until i3lock is ready.
exec i3lock --nofork --color=1e1e2e
