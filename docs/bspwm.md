# bspwm desktop

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

This is an alternative X11 session alongside i3. It keeps the same applications,
Dracula colors, three-pixel purple borders, rounded corners, ten numbered
workspaces, Rofi, Quickshell monitor/bar, media controls, screenshots, wallpaper,
and native i3lock with the animated Superman ball.

The layout uses bspwm's native `longest_side` insertion: opening a window splits
the focused tile along its longer edge. There is no autotiling listener. Picom
animates these clients over 200 ms, using a private window property set by the
bspwm external rule; the new rule does not change animation matching in i3.

## Start the session

Install `bspwm`, `sxhkd`, and `x11-utils` in addition to the shared dependencies
in [setup.md](setup.md). On this machine these packages and the display-manager
session entry are already installed. The configs are linked at
`~/.config/bspwm` and `~/.config/sxhkd`; a fresh clone can use the normal Stow
instructions. `bspwmrc` and `rules.py` must retain their executable bits.

Log out and select **bspwm** in the login screen's session selector. You can return
to i3 through the same selector. There is no need to replace the running i3 WM
or change your default login session to try it.

`bspwmrc` applies appearance, pointer behavior, desktop initialization, and rules.
A session owner starts sxhkd, Picom from the Nix profile, Quickshell, xss-lock,
network and KDE Connect applets, the policy agent, XDG autostarts, and wallpaper.
A per-user/per-display lock prevents duplicate starts on config reload or WM
restart. The owned long-running processes are stopped when the WM exits.
The Stow-linked `autostart/picom.desktop` disables the distribution's duplicate
plain Picom autostart. Only the session's `picom/start.sh` launches the compositor,
using nixGL for the Nix package's host-driver access.
Its log is `$XDG_RUNTIME_DIR/spectre-bspwm-<uid>-<DISPLAY>.log` (or `/tmp` if the
runtime directory is unset). Display names containing `/` use `_` in the filename.

The session sets `SPECTRE_WM=bspwm` and `XDG_CURRENT_DESKTOP=bspwm` for its children.
Quickshell selects its bspwm backend without opening an i3 IPC connection.
Desktop/focus/urgency changes come from bspwm events; window titles are refreshed
within one second, including title changes that bspwm does not publish.

## Familiar shortcuts

| Shortcut | Behavior |
| --- | --- |
| Super+Enter / E / B | Kitty / Thunar / Helium |
| Super+A / Backspace / F12 | Rofi / confirmed power menu / resource monitor |
| Super+L | Shared native i3lock wrapper |
| Super+Q | Request that the focused application close |
| Super+arrows or J/K/U/semicolon | Focus west/south/north/east |
| Super+Shift+arrows or J/K/L/semicolon | Swap toward that direction, or move to the next monitor at the edge |
| Super+1…9 / 0 | Focus globally named desktop 1…10 |
| Super+Shift+1…9 / 0 | Move the window to desktop 1…10 without following |
| Super+wheel up / down | Previous / next occupied desktop on the current monitor, wrapping at either end |
| Super+Tab / Super+Shift+Tab | Open the workspace switcher and cycle forward / backward while Super is held |
| Alt+Enter | Toggle fullscreen, restoring the prior state |
| Super+W / Space | Toggle floating / focus the other floating-or-tiled group |
| Super+S | Monocle view of the current desktop |
| Super+Ctrl+Tab / Super+Ctrl+Shift+Tab | Cycle windows forward / backward, including in monocle |
| Super+V | Return to tiling and rotate the focused split by 90 degrees |
| Super+R, then arrows or J/K/L/semicolon | Repeated resizing; Enter, Escape, or Super+R exits |
| Super+Shift+D | Switch longest-side / alternating insertion |
| Super+Shift+C | Reapply settings and reload this session's sxhkd |
| Super+Shift+R | Restart bspwm while preserving windows |
| Super+Shift+E | Confirm logout through Rofi |
| Super+left/right mouse drag | Move/swap / resize |
| Print / Shift+Print | Full / selected screenshot on key release |
| Audio, mic and brightness keys | Same pactl/brightnessctl controls as i3 |

Additional native tree controls: **Super+Ctrl+B** balances the desktop;
**Super+Ctrl+arrows** toggles a placement preselection, and **Super+Ctrl+Space**
cancels it. sxhkd's resize chain runs in the existing hotkey daemon; its wrapper
exports the correct PID on sxhkd 0.6.2 so exits and reloads target that instance.

### Quickshell workspace switcher

Hold Super and press Tab to open the rounded Dracula panel. It lists occupied
workspaces across monitors, plus your current workspace even when empty.
The current workspace starts first, followed by recently used workspaces;
the candidate list stays fixed during the gesture. Cards show workspace and
monitor names, application names, and a schematic of their window layout.
Repeated Tab advances; Super+Shift+Tab reverses. Release both Super keys to switch,
or press Escape to cancel without changing workspaces. Clicking a card selects
it as well. A stationary pointer never changes the keyboard selection.

The short-lived `super-release.py` helper observes X11 key state only while the
panel is open. It handles quick taps whose Super release happens before the
asynchronous IPC call maps the window, without globally intercepting Super itself.
The panel opens on the focused monitor, floats above applications, and does not
change the workspace until selection is committed.

Super+wheel is a separate sxhkd action: it works even if Quickshell is stopped.
Vertical wheel up/down and horizontal wheel left/right select previous/next
occupied desktops on the focused monitor, skipping empty and hidden-only
desktops and wrapping around. From an empty desktop, it finds the nearest
occupied desktop in the requested direction. If there is no other occupied
desktop, it does nothing. The existing 350 ms quiet interval groups touchpad
momentum into one switch per scroll burst.

## Intentional differences

- Monocle is bspwm's focused-stack experience. It does not imitate i3 container
  stacks or tab decorations. Use Super+Ctrl+Tab / Super+Ctrl+Shift+Tab to cycle its windows.
- Longest-side insertion is native and always automatic. Super+Shift+D changes
  the insertion scheme; it does not suspend an external helper.
- On first setup, desktops 1–10 are spread across the currently connected
  monitors. Names remain global: focusing desktop 7 selects its monitor.
  Reloads preserve desktop names, window placement, and layouts. Extra named
  desktops remain visible in the bar. A monitor listener replaces bspwm's
  default `Desktop` after hotplug with workspace **10** if that slot is unused.
  Otherwise it uses **11** (or the next free higher number), preserving every
  open window and leaving the lower-numbered workspaces on their existing monitors.
  After changing monitor arrangements,
  bspwm can move a desktop with `bspc desktop <name> -m <monitor>`; reload does
  not redistribute existing work.
- The bar retains the top-four-pixel trigger and at least five-second linger.
  Its backend updates monitor padding throughout the animation and clears it
  when hidden. bspwm 0.9.10 only grows padding from EWMH struts, so this session
  ignores those struts and sets padding directly. The i3 backend keeps using
  its temporary dock. No fixed padding is set aside for a hidden bar.
- LocalSend, Gedit, Bluetooth/audio settings, and KDE Connect utility windows
  float and center. The Quickshell monitor floats with its own border.

The existing i3 files continue to provide the shared wallpaper and locker.
They are reusable assets/scripts; bspwm does not start i3 or its dwindle helper.
The Polybar fallback remains configured for i3, rather than being started here.

## Validation

Tested with bspwm 0.9.10 and sxhkd 0.6.2 inside Xephyr while the host stayed in
i3. The nested session disables ordinary desktop autostarts with
`SPECTRE_BSPWM_TEST=1`; its bar, compositor, and hotkey daemon can be launched
individually against that display and a separate `BSPWM_SOCKET`.

Checks cover native tiling, directional and numbered-desktop controls,
floating/fullscreen state restoration, monocle, resize chains, non-destructive
reloads, case-insensitive utility rules, Quickshell loading, and bar reservation.
Python regression tests additionally cover desktop initialization and the
workspace/urgency model across multiple monitors. A real bspwm login is still
the final check for display-manager startup, applet ownership, and hardware
shortcuts. Lock/suspend are shared with i3 and were not triggered during tests.
