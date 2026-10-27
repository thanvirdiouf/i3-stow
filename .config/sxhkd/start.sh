#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# sxhkd 0.6.2 does not export SXHKD_PID itself. Preserve it across exec so
# modal resize and reload affect only this session's hotkey daemon.
SXHKD_PID=$$
SXHKD_SHELL=/bin/sh
export SXHKD_PID SXHKD_SHELL
exec sxhkd -c "${XDG_CONFIG_HOME:-$HOME/.config}/sxhkd/sxhkdrc"
