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
| `polybar` | Workspace, clock, audio, brightness, and system-tray bar. |
| `rofi` | Application launcher and `greenpower.sh` power menu. |
| `picom` | Compositor configured in `.config/picom/picom.conf`. |
| `kitty`, `thunar`, `mpv` | Terminal and file-manager shortcuts; configured media player. |
| `dex` | Starts XDG autostart applications when i3 starts. |
| `xss-lock`, `i3lock` | Screen locking, including before suspend. |
| `feh` | Sets the i3 wallpaper. |
| `flameshot` | Full-desktop and selected-area screenshots, saved to disk and copied to the clipboard. |
| `network-manager`, `network-manager-gnome` | Network service and `nm-applet` system-tray applet. |
| `kdeconnect` | `kdeconnect-indicator` autostart and device integration. |
| `policykit-1-gnome` | Authentication agent explicitly started by i3. |
| `pulseaudio-utils`, `pavucontrol` | `pactl` volume/microphone shortcuts and Polybar's audio settings menu. |
| `brightnessctl` | Backlight brightness keys. |
| `ddcutil` | External-monitor brightness polling and scrolling in Polybar. |
| `xdg-desktop-portal`, `xdg-desktop-portal-gtk`, `gnome-keyring` | GTK desktop portals and the configured keyring secret portal. |
| `fontconfig` | Discovers the bundled Nerd Fonts and supplies `fc-cache`. |
| `python3` | Both i3 helpers; they use only Python's standard library. |
| `bash`, `coreutils`, `grep`, `mawk`, `util-linux`, `systemd` | Shell/scripts, `readlink`, `sleep`, `awk`, `flock`, `systemctl`, and `loginctl`; normally already installed. |
| `psmisc`, `i3status` | `killall` and the legacy i3status refresh command still used by the audio bindings; the visible bar is Polybar. |
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
  gnome-keyring fontconfig python3 bash coreutils grep mawk util-linux \
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
  --ignore='^docs(/|$)' \
  --ignore='^\.local/share/nvim(/|$)' .
```

If the preview looks correct, apply it:

```sh
stow --verbose --no-folding --target="$HOME" \
  --ignore='(^|/)(\.git|\.gitignore|\.agents|\.aws|\.codex)(/|$)' \
  --ignore='(^|/)(README|COPYING)\.md$' \
  --ignore='^docs(/|$)' \
  --ignore='^\.local/share/nvim(/|$)' .
```

`--no-folding` keeps target directories as real directories and links individual
files. The ignore rules exclude repository metadata, local tool directories,
documentation, and Neovim runtime data. `.gitignore` controls Git tracking;
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

