#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# See COPYING.md in the repository root for the license text.

# Point to your custom theme
THEME="$HOME/.config/rofi/config.rasi"
WAKE_LOCK_UNIT="rofi-wake-lock.service"

# Define menu options
POWEROFF="⏻ Power Off"
REBOOT="⟳ Reboot"
SUSPEND="⏾ Suspend"
LOGOUT="➜ Log Out"
if systemctl --user is-active --quiet "$WAKE_LOCK_UNIT"; then
  WAKE_LOCK="󰅶 Wake Lock On · Turn Off"
  wake_lock_active=true
else
  WAKE_LOCK="󰅶 Wake Lock Off · Turn On"
  wake_lock_active=false
fi

# 1. Display the main menu
# Overrides window size to be smaller and disables the text entry field
chosen=$(printf '%s\n' "$POWEROFF" "$REBOOT" "$SUSPEND" "$LOGOUT" "$WAKE_LOCK" | rofi -dmenu -i -no-custom \
  -theme "$THEME" \
  -theme-str 'mainbox {spacing: 1%;} window {width: calc(20% max 300px); height: 32%; background-image: none; padding: 1%;} entry {enabled: false;} listview {lines: 5;} element {padding: calc(1% + 4px) 1%;}' \
  -p "Power")

# Exit immediately if the user escapes/cancels
[[ -z "$chosen" ]] && exit 1

# 2. Reusable confirmation prompt function
confirm_action() {
  local action=$1
  # Overrides window to be even smaller for the Yes/No prompt
  local res=$(printf "Yes\nNo" | rofi -dmenu -i \
    -theme "$THEME" \
    -theme-str 'window {width: 15%; height: 25%; background-image: none; padding: 1%;} entry {enabled: false;} listview {lines: 2;}' \
    -p "$action?")
  [[ "$res" == "Yes" ]] && return 0 || return 1
}

# 3. Execute the command based on the selection
case "$chosen" in
"$WAKE_LOCK")
  if "$wake_lock_active"; then
    systemctl --user stop "$WAKE_LOCK_UNIT" || rofi -e "Could not turn off the wake lock."
  elif ! systemd-run --user --quiet --collect --unit="$WAKE_LOCK_UNIT" \
    --service-type=notify --property=TimeoutStartSec=10s \
    --setenv="DISPLAY=$DISPLAY" --setenv="XAUTHORITY=${XAUTHORITY:-$HOME/.Xauthority}" \
    -- python3 "$(dirname -- "${BASH_SOURCE[0]}")/wake-lock.py"; then
    rofi -e "Could not turn on the wake lock."
  fi
  ;;
"$POWEROFF")
  confirm_action "Power Off" && systemctl poweroff
  ;;
"$REBOOT")
  confirm_action "Reboot" && systemctl reboot
  ;;
"$SUSPEND")
  confirm_action "Suspend" && systemctl suspend
  ;;
"$LOGOUT")
  confirm_action "Log Out" && loginctl kill-session $XDG_SESSION_ID
  ;;
*) exit 1 ;;
esac
