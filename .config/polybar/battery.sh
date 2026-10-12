#!/usr/bin/env bash

# Battery and AC adapter names from /sys/class/power_supply.
battery=/sys/class/power_supply/BAT1
adapter=/sys/class/power_supply/ACAD
warning_color=${1:-#E5C07B}
critical_color=${2:-#A54242}

read -r capacity < "$battery/capacity" || exit 1
read -r status < "$battery/status" || exit 1
[[ "$capacity" =~ ^[0-9]+$ ]] || exit 1
capacity=$((10#$capacity))
(( capacity <= 100 )) || exit 1

online=0
if [[ -r "$adapter/online" ]]; then
    read -r online < "$adapter/online"
fi

icons=(    )
icon=${icons[$((capacity * 5 / 101))]}
if [[ "$status" == Full ]] || (( capacity == 100 )); then
    icon=
elif [[ "$status" == Charging ]]; then
    icon=
elif [[ "$online" == 1 ]]; then
    icon=
fi

# Highlight low charge only while running on battery power.
color=
if [[ "$online" != 1 && "$status" != Charging ]]; then
    if (( capacity <= 15 )); then
        color=$critical_color
    elif (( capacity <= 30 )); then
        color=$warning_color
    fi
fi

if [[ -n "$color" ]]; then
    printf '%%{F%s}%s%% %s%%{F-}\n' "$color" "$capacity" "$icon"
else
    printf '%s%% %s\n' "$capacity" "$icon"
fi
