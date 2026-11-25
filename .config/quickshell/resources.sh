#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Compile once per source version. Concurrent shell instances publish atomically.
set -eu
src=$(dirname -- "$(readlink -f -- "$0")")/resources.c
cache=${XDG_CACHE_HOME:-$HOME/.cache}/quickshell
mkdir -p -- "$cache"
digest=$(sha256sum -- "$src")
bin="$cache/resources-$(uname -m)-${digest%% *}"
if [ ! -x "$bin" ]; then
    tmp=$(mktemp -- "$cache/.resources-XXXXXX")
    trap 'rm -f -- "$tmp"' EXIT
    cc -std=c11 -O2 -Wall -Wextra "$src" -o "$tmp" $(pkg-config --cflags --libs glib-2.0) -lm
    chmod 0755 "$tmp"
    mv -f -- "$tmp" "$bin"
fi
exec "$bin" "$@"
