# Dotfiles

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

My Linux/X11 desktop, built around i3 and managed with GNU Stow.

![i3 desktop with rounded purple borders and a translucent kitty terminal](docs/screenshots/desktop.png)

## Polybar

Workspaces, window title, clock, volume, battery, brightness, and system tray.

![Polybar close-up showing workspace buttons, clock, audio, battery, brightness, and tray](docs/screenshots/polybar.png)

## Rofi

| Application launcher | Power menu |
| --- | --- |
| ![Rofi application launcher with Dracula colors](docs/screenshots/rofi-launcher.png) | ![Rofi power menu with Dracula colors](docs/screenshots/rofi-power-menu.png) |

<details>
<summary>Dwindle tiling preview</summary>

![Three kitty windows arranged by i3's dwindle autotiling](docs/screenshots/tiling.png)

</details>

<details>
<summary>Animated lockscreen preview</summary>

![Purple lock emblem rendered by Picom; the emblem rotates while locked](docs/screenshots/lockscreen.png)

</details>

## What's included

- **i3:** dwindle autotiling, gaps, and rounded purple borders.
- **Picom + kitty:** blur, shadows, and Catppuccin Mocha terminal colors.
- **Lockscreen:** an animated purple lock emblem with i3lock password feedback.
- **Rofi:** Dracula launcher and a power menu with confirmation prompts.
- **Polybar:** a compact bar with audio and brightness controls.

Neovim/LazyVim, Bash, mpv, and desktop-portal settings are also included.

## Setup

```sh
git clone https://github.com/thanvirdiouf/i3-stow.git "$HOME/.dotfiles"
cd "$HOME/.dotfiles"
```

Follow the [setup guide](docs/setup.md) for dependencies, Stow commands, and
machine-specific adjustments. Stow links configurations; it does not install apps.

## Essential shortcuts

| Shortcut | Action |
| --- | --- |
| `Super+Enter` | Open kitty |
| `Super+A` / `Super+Backspace` | Launcher / power menu |
| `Super+1`–`0` | Switch workspace |
| `Super+Shift+D` | Toggle dwindle autotiling |
| `Super+L` | Lock the screen |
| `Print` / `Shift+Print` | Full-desktop / area screenshot |
| `Super+Shift+C` | Reload i3 |

More bindings are in the [i3 config](.config/i3/config).

## License

[![GNU GPLv3](https://www.gnu.org/graphics/gplv3-127x51.png)](COPYING.md)

Original code, configuration, and documentation: **GPL-3.0-or-later**
([COPYING.md](COPYING.md)). Bundled third-party files retain their own licenses.
