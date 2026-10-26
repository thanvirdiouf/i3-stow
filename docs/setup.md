# Setup and reference

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

[Back to README](../README.md)

## Contents

```text
.
├── .bashrc                     # Bash history, prompt, aliases, and tool paths
├── .inputrc                    # Readline configuration
├── .config
│   ├── i3                      # Window manager configuration and wallpaper
│   ├── kitty                   # Terminal configuration and theme
│   ├── mpv                     # Media player keybindings
│   ├── nvim                    # Neovim / LazyVim configuration
│   ├── picom                   # Compositor configuration
│   ├── polybar                 # Status bar and external-monitor brightness script
│   ├── quickshell              # Dracula bar and live resource monitor for i3/X11
│   ├── rofi                    # Launcher theme, background, and power menu
│   └── xdg-desktop-portal      # Desktop portal configuration
├── docs                        # Setup guide and screenshots
└── .local
    ├── bin                     # Local executable directory
    ├── opt/ast-grep             # Bundled ast-grep executables
    └── share
        ├── fonts               # Agave and JetBrains Mono Nerd Fonts
        └── nvim                # Local Neovim data
```

Some directories may be local or untracked. Git records files, so empty
directories such as `.local/bin` will not appear in a fresh clone.

## Setup

Install Git and GNU Stow using your distribution's package manager, then clone
this repository into `~/.dotfiles`:

```sh
git clone https://github.com/thanvirdiouf/i3-stow.git "$HOME/.dotfiles"
cd "$HOME/.dotfiles"
```

Stow links files; it does not install applications or their dependencies.

### Package dependencies (APT)

The following list covers the active configurations and scripts in this
repository. Package names are for Debian/Ubuntu-based distributions; they were
checked against this machine's Linux Mint 22.3 / Ubuntu 24.04 APT indexes.
APT installs the packages' library dependencies automatically.

| Packages | Used by / purpose |
| --- | --- |
| `git`, `stow` | Clone the repository, link dotfiles, and download Neovim plugins. |
| `xserver-xorg`, `dbus-x11` | X11 desktop session and D-Bus support. |
| `i3-wm` | Window manager; also supplies `i3-msg` and `i3-nagbar`. |
| `polybar` | Optional fallback bar. |
| `rofi` | Default application launcher and `greenpower.sh` power menu. |
| `picom` | Compositor configured in `.config/picom/picom.conf`. |
| `kitty`, `thunar`, `mpv` | Terminal and file-manager shortcuts; configured media player. |
| `dex` | Starts XDG autostart applications when i3 starts. |
| `xss-lock`, `i3lock` | Screen locking, including before suspend. |
| `feh` | Sets the i3 wallpaper. |
| `flameshot` | Full-desktop and selected-area screenshots, saved to disk and copied to the clipboard. |
| `network-manager`, `network-manager-gnome` | Network service and `nm-applet` system-tray applet. |
| `kdeconnect` | `kdeconnect-indicator` autostart and device integration. |
| `policykit-1-gnome` | Authentication agent explicitly started by i3. |
| `pulseaudio-utils`, `pavucontrol` | `pactl` volume/microphone shortcuts and the bar's audio settings menu. |
| `brightnessctl` | Backlight brightness keys. |
| `ddcutil` | External-monitor brightness polling and scrolling in both bars. |
| `xdg-desktop-portal`, `xdg-desktop-portal-gtk`, `gnome-keyring` | GTK desktop portals and the configured keyring secret portal. |
| `fontconfig` | Discovers the bundled Nerd Fonts and supplies `fc-cache`. |
| `python3`, `libglib2.0-bin`, `x11-xserver-utils` | i3 helpers, resource sampler, GIO application launching, and `xrandr` lock artwork sizing. |
| `bash`, `coreutils`, `grep`, `mawk`, `util-linux`, `systemd` | Shell/scripts, `readlink`, `sleep`, `awk`, `flock`, `systemctl`, and `loginctl`; normally already installed. |
| `psmisc`, `i3status` | `killall` and the legacy i3status refresh command still used by the audio bindings. |
| `neovim`, `fd-find`, `ripgrep` | Editor, explicitly configured `fdfind` file picker, and plugin text searches. |
| `tree-sitter-cli`, `build-essential` | Tree-sitter CLI and C compiler for Neovim syntax parsers. |
| `curl`, `ca-certificates`, `tar`, `gzip`, `unzip` | Download and extract Neovim plugin/tool assets. |
| `python3-venv` | Creates the Python provider environment configured for Neovim. |

Install the desktop applications and editor prerequisites:

```sh
sudo apt update
sudo apt install \
  git stow xserver-xorg dbus-x11 \
  i3-wm i3status polybar rofi picom kitty thunar mpv \
  dex xss-lock i3lock feh flameshot network-manager network-manager-gnome \
  kdeconnect policykit-1-gnome pulseaudio-utils pavucontrol \
  brightnessctl ddcutil xdg-desktop-portal xdg-desktop-portal-gtk \
  gnome-keyring fontconfig python3 libglib2.0-bin x11-xserver-utils bash coreutils grep mawk util-linux \
  systemd psmisc neovim fd-find ripgrep tree-sitter-cli build-essential \
  curl ca-certificates tar gzip unzip python3-venv
```

Version requirements matter: the gaps configuration needs
[i3 4.22 or later](https://i3wm.org/docs/userguide.html#gaps), and `internal/tray`
needs [Polybar 3.7 or later](https://polybar.github.io/2023/11/05/Release-3.7.0.html).
The pinned [nvim-treesitter revision](https://github.com/nvim-treesitter/nvim-treesitter/blob/e289100ff98969e118c702199d88b764ce9e7fdf/README.md#requirements)
requires Neovim **0.12.0+** and tree-sitter CLI **0.26.1+**. Ubuntu 24.04's stock
`neovim` (0.9.5) and `tree-sitter-cli` (0.20.8) are too old; obtain compatible
versions separately if your APT repositories do not provide them. Installing
the command above alone does not satisfy these editor version requirements.

### Additional setup and optional tools

- **Audio server:** Polybar and `pactl` need a running PulseAudio-compatible
  server. Keep the existing desktop audio service. If none is installed, use
  `sudo apt install pipewire-pulse wireplumber` for PipeWire, or
  `sudo apt install pulseaudio` for PulseAudio, choosing one setup.
- **Helium:** `Super+B` executes `helium`. Install that browser separately and
  ensure its executable is on `PATH`, or change the binding to your browser.
  The keybinding and local `helium.desktop` entry disable startup notifications
  so launches from i3 and Rofi open on the current workspace.
  There is no `helium` package in this machine's configured APT indexes.
- **Rust environment:** `.bashrc` unconditionally sources `~/.cargo/env`.
  Install the Rust toolchain through rustup to create it, or guard/remove that
  line if you do not use Rust. Adding a directory to `PATH` does not install it.
- **Shell enhancements:** `eza` and `starship` are optional and checked before
  use. Install them if desired; `eza` is available from this machine's Ubuntu
  indexes, while Starship may need a separate upstream installation.
- **Other GUI apps:** `gedit`, `blueman` (`blueman-manager`), and LocalSend are
  mentioned only in i3 floating-window rules. They are optional and are not
  launched by the config. Gedit and Blueman can be installed with
  `sudo apt install gedit blueman`; obtain LocalSend separately if needed.
- **Session utilities:** `xinit` is optional if you start X11 with `startx`
  instead of a display manager. `libpam-gnome-keyring` is optional for keyring
  unlocking at login; `tree` is used by the maintenance example below.
- **Compositor startup:** i3 does not explicitly launch Picom. Start `picom`
  through your session's autostart mechanism to apply its configured effects.
- **Monitor access:** `.config/polybar/monitor-brightness.sh` hardcodes I2C bus
  `3`. Adjust it for your display, enable DDC/CI on the monitor, and ensure your
  user can access the appropriate `/dev/i2c-*` device (with `i2c-dev` loaded).
- **Authentication agent:** check the hardcoded
  `/usr/lib/policykit-1-gnome/polkit-gnome-authentication-agent-1` path if using
  a different distribution or authentication-agent package.

### Quickshell

The default session uses Quickshell. The config in `.config/quickshell`
was tested with **Quickshell 0.3.2** under i3/X11 using `nixGL quickshell`.
It uses the same Dracula colors as i3/Rofi, rounded surfaces, and the bundled
JetBrains Mono Nerd Font. Edit `Theme.qml` for colors, sizing, and spacing.
The Qt cursor uses **Bibata-Modern-Ice**, matching GTK. Install that cursor theme
under `/usr/share/icons` or `/usr/local/share/icons`, or adjust the `XCURSOR_THEME`
and `XCURSOR_PATH` pragmas at the top of `shell.qml`. Cursor changes require a
Quickshell restart; the hand pointer over clickable buttons is intentional.

Install Quickshell and nixGL separately through your Nix setup. It also needs
a running **PipeWire** service for audio controls, **UPower** (`upower`) for
battery status, and **Adwaita** (`adwaita-icon-theme`) for tray menu icons.
It reuses the existing `i3-msg`, `rofi`, `pavucontrol`, `brightnessctl`, and
`ddcutil` dependencies. Battery status is hidden when no battery is present;
unavailable audio or brightness shows a dash.

After Stow has linked the config, start it in a terminal:

```sh
polybar-msg cmd quit # Only needed if Polybar is currently running.
i3-msg 'gaps top all set 0'
nixGL quickshell --no-duplicate
```

Quickshell starts automatically at the next login. Its dock reserves its own
height, including the transparent margins, so keep `gaps top 0` in i3. The normal
10 px inner gap remains between the dock and tiled windows. The Picom config
excludes this dock from effects that would fill or shadow its transparent
margins. Reload Picom after linking an updated compositor config.

For the Polybar fallback, stop Quickshell, swap the commented startup lines in
`.config/i3/config`, and change `gaps top 0` to `gaps top 38`. For the current
session:

```sh
nixGL quickshell kill
i3-msg 'gaps top all set 38'
polybar --reload --config="$HOME/.config/polybar/config.ini" example
```

| Control | Action |
| --- | --- |
| Launcher icon / `Super+A` | Open the Rofi application launcher. |
| Monitor icon / `Super+F12` | Toggle the live system monitor. |
| Workspace number | Switch workspace; scrolling cycles workspaces on the focused output. |
| Clock | Toggle time/date; hover for the full date. |
| Audio | Click to mute, scroll in 5% steps (capped at 100%), right-click for Pavucontrol. |
| Brightness | Scroll in 5% steps; click to refresh the reading. |
| Tray icon | Left/middle/right-click and scroll invoke the application's tray actions. |
| Power icon | Open the existing Rofi power menu with its confirmation prompts. |

The bar appears on each connected screen. Laptop panels use `brightnessctl`;
external displays reuse `.config/polybar/monitor-brightness.sh`, including its
machine-specific **I2C bus 3** setting and lock. Change that helper for a
different monitor; multiple external displays need a helper per display.

The tray supports **StatusNotifier/AppIndicator** applications directly and
starts **xembedsniproxy** for legacy XEmbed icons, including `nm-applet`, the
Intel/NVIDIA PRIME applet, and Mint's update/report icons. The bridge is owned
by Quickshell and stops with it. Polybar must be stopped, not hidden, before
starting the bridge: only one process can own the XEmbed tray selection.

Use a distribution-provided `xembedsniproxy` / `xembed-sni-proxy` on `PATH`, or
install the small user-local copy on Debian/Ubuntu/Mint:

```sh
bash "$HOME/.config/quickshell/install-tray-bridge.sh"
```

The installer downloads the configured APT repository's `plasma-workspace`
package and extracts only its bridge binary and license into
`~/.local/share/quickshell/xembed-sni-proxy/`. It does not install Plasma.
It checks that the required runtime libraries are available; on this machine
they were already installed. Package/version metadata is saved alongside the
binary. Re-run the installer to update it. Missing libraries are listed rather
than installed automatically.

The launcher keeps the system Qt 5 bridge's library/plugin paths separate from
Nix's Qt 6 Quickshell runtime. `tray-action.py` uses Python's standard library
and `busctl` to forward legacy clicks at the icon's screen position, including
native right-click menus which do not expose a DBusMenu handle. Existing applet
startup commands can remain unchanged.

Quickshell reloads saved QML changes automatically. To run from the repository
before linking it with Stow, use:

```sh
nixGL quickshell --path "$HOME/.dotfiles/.config/quickshell" --no-duplicate
```

See the [Quickshell type reference](https://quickshell.org/docs/v0.3.2/types/)
for the native i3, PipeWire, UPower, and tray APIs.

### pip packages

Neovim's Python provider points to a virtual environment outside the tracked
configuration. Create it and install `pynvim` before using Python-dependent
plugins. The `python3-venv` APT package above supplies pip inside the environment:

```sh
python3 -m venv "$HOME/.local/share/nvim/venv"
"$HOME/.local/share/nvim/venv/bin/python" -m pip install pynvim
```

Lazy.nvim downloads the Lua plugins on first launch; Mason manages configured
language servers and formatters. Their runtime dependencies depend on the tools
you enable. `.config/nvim/lua/plugins/example.lua` returns an empty spec, so its
example Pyright, TypeScript, and linting tools are not active dependencies.
Nerd Fonts and ast-grep executables are already bundled in this repository.

### Link the dotfiles

The repository itself is one Stow package (`.`), rather than a collection of
separate application packages. Preview the links first:

```sh
cd "$HOME/.dotfiles"
stow --simulate --verbose --no-folding --target="$HOME" \
  --ignore='(^|/)(\.git|\.gitignore|\.agents|\.aws|\.codex)(/|$)' \
  --ignore='(^|/)(README|COPYING)\.md$' \
  --ignore='^(docs|tests)(/|$)' \
  --ignore='^\.local/share/nvim(/|$)' .
```

If the preview looks correct, apply it:

```sh
stow --verbose --no-folding --target="$HOME" \
  --ignore='(^|/)(\.git|\.gitignore|\.agents|\.aws|\.codex)(/|$)' \
  --ignore='(^|/)(README|COPYING)\.md$' \
  --ignore='^(docs|tests)(/|$)' \
  --ignore='^\.local/share/nvim(/|$)' .
```

`--no-folding` keeps target directories as real directories and links individual
files. The ignore rules exclude repository metadata, local tool directories,
documentation, tests, and Neovim runtime data. `.gitignore` controls Git tracking;
Stow does not use it to decide what to link.

If Stow reports a conflict, inspect and back up the existing target file, then
move it out of the way before retrying. Avoid using `--adopt` casually: it moves
existing target files into this repository and can replace its configurations.

### Neovim configuration

`.config/nvim` is tracked as regular files and is included in a fresh clone.
Install the editor dependencies and compatible versions described above before
starting Neovim.

### Fonts

After linking the fonts, refresh the font cache if Fontconfig is installed:

```sh
fc-cache -f
```

Font licenses are included alongside the font files. Bundled ast-grep binaries
must be compatible with the target machine's operating system and architecture.

### Screenshot shortcuts

- **Print Screen:** capture the whole desktop (all monitors).
- **Shift+Print Screen:** drag to select an area; capture completes when you
  release the mouse. Press **Escape** to cancel.

Both shortcuts save PNG images to `~/Pictures/Screenshots` (created automatically)
and copy the image to the clipboard. They use Flameshot. After changing the i3
configuration, press **Super+Shift+C** to reload it.

### i3 dwindle layout

The i3 config starts `.config/i3/dwindle.py` automatically (Python 3, no extra
packages). New tiled windows divide the focused tile along its longer edge,
creating nested splits. Existing windows are not rearranged. Floating windows,
fullscreen containers, and tabbed/stacked layouts are left alone.

Press **Super+Shift+D** to toggle automatic splitting for the current session.
Normal focus, move, and resize shortcuts still work. To disable it permanently,
remove the helper's `exec_always` line and its toggle binding from the i3 config,
then stop the running helper and reload i3. Reloads cannot start duplicate helpers.

### Application launcher and resource monitor

**Super+A** and the bar's application button open **Rofi** with the existing
Dracula theme. Rofi is also the target of `control.sh launcher` and the shell's
`desktop launcher` IPC action; it works without Quickshell running.

**Super+F12** and the monitor icon toggle the Quickshell system monitor. It
shares the bar's `Theme.qml`: Dracula surfaces, purple outlines, rounded corners,
and JetBrains Mono Nerd Font. i3 floats and centers the window. Press **Escape**
or its close button to dismiss it. If Quickshell is stopped, its shortcut
displays a notice.

The earlier QML launcher and static lock artwork files remain available in the
repository as optional components, but the active shell does not instantiate
the launcher or generate cached lock artwork.

The monitor samples every two seconds while open and stops its Python process
when dismissed. It shows CPU utilization, available-memory based RAM usage,
root filesystem capacity, swap, aggregate network rates (excluding loopback),
CPU temperature when supported by hwmon, uptime, load, and seven processes
ranked by CPU and then resident memory. Process CPU uses **100% per core**;
overall CPU is normalized across all cores. Graphs keep the last 45 samples;
the network graph scales to its largest retained sample. Disk capacity describes
`/`, and network totals can include virtual interfaces. No process controls are
provided. The sampler uses Python's standard library and Linux `/proc`/`/sys`.

### Animated lockscreen

**Super+L**, idle locking, and locking before suspend all use
`.config/i3/lock.sh`. It directly execs **`i3lock --nofork --color=1e1e2e`** with the prepared
`lockscreen-image.png` when available, preserving xss-lock's sleep file descriptor until i3lock has secured the screen.
The image is prepared once; no QML rendering or image conversion runs during locking.

Picom's GLX backend applies `.config/picom/lockscreen.frag` only to the i3lock
window. It draws a spinning purple ball with the supplied Superman shield and subtle
moving contours. The shader keys out the photo's blue backdrop while retaining
the red/gold artwork. If the PNG is missing, it draws the original purple padlock.
The ball remains visible inside the native typing ring: the shader removes only
i3lock's flat indicator fills within the sphere, preserving the keypress arcs,
status rings, authentication messages, and Caps Lock text above it. i3lock owns authentication and the keyboard/pointer
grabs; Picom only supplies visuals. The lock window stays opaque, square-cornered,
and free of fades, blur, and shadows. Without Picom, it is still a normal solid
dark i3lock screen with password feedback; when the PNG is used, its source
patch remains visible in the top-left corner.

Keep `BACKGROUND` in the shader synchronized with the wrapper's `--color`:
the shader recognizes untouched background pixels by this exact color and
identifies the stock indicator fills composited over that background. The fill
colors match i3lock 2.14.1. Change `seconds * 0.65` to adjust rotation
speed. On multiple monitors the ball is centered on the combined desktop;
native i3lock indicators retain their per-monitor layout.

The prepared image matches the current **1920×1080** desktop and carries its
texture in a marked 256×256 corner, away from the password indicator. Regenerate
it after display-layout changes. See [the image setup guide](../.config/i3/CUSTOM-LOCKSCREEN-IMAGE.md)
for the source, rebuild commands, shader settings, and original-padlock fallback.

This animation is produced by Picom on X11. Quickshell's secure session-lock
API is Wayland-only; a normal QML window cannot replace i3lock's security role.
The static QML lockscreen design from the previous revision remains in the
repository but is not active.

After changing the configuration, press **Super+Shift+C** to reload i3.
Quickshell reloads its QML automatically. Picom normally reloads its configuration;
if needed, restart its existing process with `pkill -USR1 -u "$(id -u)" -x picom`.
The xss-lock command is unchanged, so its listener does not need restarting.

Run the regression checks from the repository:

```sh
python3 -m unittest discover -s tests -v
```

## Maintaining the links

Edit configurations inside `~/.dotfiles`, then review and commit the changes
with Git. Existing symlinks reflect file edits immediately; applications may
need a reload or restart.

After adding or moving files, rerun the linking command above with `--restow`.
To remove this package's symlinks, run the same command with `--delete` instead.
Keep the same target and ignore rules for both operations. Unstowing leaves the
source files in this repository intact.

Inspect the layout and pending changes with:

```sh
tree -a -L 2
git status --short
git diff
```

Keep credentials and machine-specific secrets out of Git. The local `.aws`,
`.agents`, and `.codex` directories are excluded from the linking commands above.

