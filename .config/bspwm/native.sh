#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
config_dir=${0%/*}
cache=${XDG_CACHE_HOME:-$HOME/.cache}/spectre-desktop-helpers

case ${1-} in
    build)
        shift
        if ! command -v cargo >/dev/null 2>&1; then
            PATH=${CARGO_HOME:-$HOME/.cargo}/bin:$PATH
            export PATH
        fi
        mkdir -p -- "$cache/bin"
        exec 9>"$cache/build.lock"
        flock 9
        cargo build --locked --release --manifest-path "$config_dir/native/Cargo.toml" \
            --target-dir "$cache/target" "$@"
        # Keep the running session's helpers available throughout a rebuild.
        for helper in scroll window-rules super-release; do
            tmp=$(mktemp -- "$cache/bin/.helper-XXXXXX")
            trap 'rm -f -- "$tmp"' EXIT
            install -m 755 -- "$cache/target/release/$helper" "$tmp"
            mv -f -- "$tmp" "$cache/bin/$helper"
            trap - EXIT
        done
        exit
        ;;
    scroll|super-release) helper=$1; shift ;;
    [0-9]*) helper=window-rules ;; # bspwm passes the X11 window ID first.
    *) printf '%s\n' 'Usage: native.sh build | scroll next|prev | super-release' >&2; exit 2 ;;
esac

if [ -x "$cache/bin/$helper" ]; then
    exec "$cache/bin/$helper" "$@"
fi
case $helper in
    scroll) exec python3 "$config_dir/actions.py" scroll "$@" ;;
    window-rules) exec "$config_dir/rules.py" "$@" ;;
    super-release) exec python3 "$config_dir/../quickshell/super-release.py" "$@" ;;
esac
