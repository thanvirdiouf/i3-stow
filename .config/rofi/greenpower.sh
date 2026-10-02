#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# See COPYING.md in the repository root for the license text.

# Point to your custom theme
THEME="$HOME/.config/rofi/config.rasi"

# Define menu options
POWEROFF="⏻ Power Off"
REBOOT="⟳ Reboot"
SUSPEND="⏾ Suspend"
LOGOUT="➜ Log Out"

# 1. Display the main menu
# Overrides window size to be smaller and disables the text entry field
chosen=$(printf "%s\n%s\n%s\n%s" "$POWEROFF" "$REBOOT" "$SUSPEND" "$LOGOUT" | rofi -dmenu -i \
  -theme "$THEME" \
  -theme-str 'mainbox {spacing: 1%;} window {width: 20%; height: 25%; background-image: none; padding: 1%;} entry {enabled: false;} listview {lines: 4;} element{padding: 1%;}' \
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
