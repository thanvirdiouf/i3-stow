#!/usr/bin/env bash

# Acer PM161Q B1 on HDMI. Update this if its I2C bus changes.
bus=3

# Serialize polling and scroll events so DDC transactions cannot overlap.
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/polybar-brightness-${UID}-${bus}.lock"
flock -w 10 9 || exit 1

case "${1:-read}" in
    up)
        LC_ALL=C ddcutil --bus "$bus" setvcp 10 + 5
        exit $?
        ;;
    down)
        LC_ALL=C ddcutil --bus "$bus" setvcp 10 - 5
        exit $?
        ;;
    read) ;;
    *) exit 2 ;;
esac

# Retry brief communication failures without treating error text as a value.
for attempt in 1 2 3; do
    if output=$(LC_ALL=C ddcutil --bus "$bus" --brief getvcp 10); then
        value=$(awk '$1 == "VCP" && $2 == "10" && $3 == "C" && $4 ~ /^[0-9]+$/ { print $4; exit }' <<< "$output")
        if [[ -n "$value" ]]; then
            printf '%s\n' "$value"
            exit 0
        fi
    fi
    if (( attempt < 3 )); then
        sleep 0.2
    fi
done

exit 1
