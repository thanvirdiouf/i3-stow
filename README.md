# Dotfiles

[![GNU GPLv3](https://www.gnu.org/graphics/gplv3-127x51.png)](COPYING.md)

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Personal Linux dotfiles managed with GNU Stow. This repository lives at
`~/.dotfiles` and mirrors the home directory: Stow creates symlinks in `~`
pointing to the files here, so edits stay in one place.

## Contents

```text
.
├── .bashrc                     # Bash history, prompt, aliases, and tool paths
├── .inputrc                    # Readline configuration
├── .config
│   ├── i3                      # Window manager configuration and wallpaper
│   ├── kitty                   # Terminal configuration and theme
│   ├── mpv                     # Media player keybindings
│   ├── nvim                    # Neovim configuration (embedded Git repository)
│   ├── picom                   # Compositor configuration
│   ├── rofi                    # Launcher theme, background, and power menu
│   └── xdg-desktop-portal      # Desktop portal configuration
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
this repository into `~/.dotfiles` (replace the placeholder with its Git URL):

```sh
git clone <repository-url> "$HOME/.dotfiles"
cd "$HOME/.dotfiles"
```

Install the applications whose configurations you want to use separately.
Stow links files; it does not install applications or their dependencies.
Review the configs for machine-specific commands and paths before using them.
For example, `.bashrc` sources `~/.cargo/env` and optionally loads NVM,
Starship, and eza; the i3 config starts several desktop utilities.

### Link the dotfiles

The repository itself is one Stow package (`.`), rather than a collection of
separate application packages. Preview the links first:

```sh
cd "$HOME/.dotfiles"
stow --simulate --verbose --no-folding --target="$HOME" \
  --ignore='(^|/)(\.git|\.gitignore|\.agents|\.aws|\.codex)(/|$)' \
  --ignore='(^|/)(README|COPYING)\.md$' \
  --ignore='^\.local/share/nvim(/|$)' .
```

If the preview looks correct, apply it:

```sh
stow --verbose --no-folding --target="$HOME" \
  --ignore='(^|/)(\.git|\.gitignore|\.agents|\.aws|\.codex)(/|$)' \
  --ignore='(^|/)(README|COPYING)\.md$' \
  --ignore='^\.local/share/nvim(/|$)' .
```

`--no-folding` keeps target directories as real directories and links individual
files. The ignore rules exclude repository metadata, local tool directories,
documentation, and Neovim runtime data. `.gitignore` controls Git tracking;
Stow does not use it to decide what to link.

If Stow reports a conflict, inspect and back up the existing target file, then
move it out of the way before retrying. Avoid using `--adopt` casually: it moves
existing target files into this repository and can replace its configurations.

### Neovim checkout

`.config/nvim` is currently recorded as a Gitlink, but this repository has no
`.gitmodules` file. A fresh clone therefore does not include the Neovim
configuration automatically. Populate that directory from its own repository
before linking it, or configure it as a proper submodule with a source URL.

### Fonts

After linking the fonts, refresh the font cache if Fontconfig is installed:

```sh
fc-cache -f
```

Font licenses are included alongside the font files. Bundled ast-grep binaries
must be compatible with the target machine's operating system and architecture.

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

## License

Original code, configuration, and documentation in this repository are licensed
under the GNU General Public License, version 3 or (at your option) any later
version (**GPL-3.0-or-later**). See [COPYING.md](COPYING.md) for the full GPLv3 text.

You may redistribute and modify these works under those terms. They are provided
without any warranty, including the implied warranties of merchantability or
fitness for a particular purpose.

Bundled third-party files retain their respective licenses and copyright notices;
the repository license does not relicense them. This includes Nerd Fonts, bundled
ast-grep executables, the separate Neovim repository, and third-party images or
configuration templates. See the font directories' license files and upstream
projects for their terms.

The [official GNU GPLv3 logo](https://www.gnu.org/graphics/license-logos.html)
is in the public domain.
