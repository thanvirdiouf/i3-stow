# Put your own image on the lockscreen ball

> Legacy reference: the active lockscreen now uses Quickshell artwork and
> i3lock authentication. See [the current setup notes](../../docs/setup.md#quickshell-lockscreen-artwork-on-x11).
> The Picom lock shader is disabled. This older recipe requires restoring its
> shader rules as well as changing the wrapper; it does not apply to the active QML design.

This tutorial adapts the existing rotating purple ball to show a circular photo,
avatar, or logo on both sides. It keeps the lighting, rotation, background, and
i3lock's real password feedback. These instructions are for this setup's current
**single 1920×1080 display**, stock i3lock, and Picom GLX backend.

Creating this document does not apply the changes below.

## How the image gets into the shader

Picom supplies the lock window as the shader's `tex` texture. Declaring another
sampler does not make Picom load an image from disk.

Instead, make an opaque lockscreen PNG with a 256×256 copy of your image in its
top-left corner. Pass that PNG to i3lock. The shader reads that corner as its
image source, hides the flat copy, and maps it onto the rotating ball.

The current shader treats pixels that differ from the plain background as
password feedback. We must exclude the image-source corner from that check, or
the flat image will remain visible. The native password indicator stays in the
center, outside that corner.

## 1. Back up the two files you will edit

Run these commands in one terminal and keep it open for the rollback commands:

```sh
cd "$HOME/.dotfiles"
mkdir -p "$HOME/.local/state/lockscreen-backups"
backup_dir=$(mktemp -d "$HOME/.local/state/lockscreen-backups/custom-image.XXXXXX")
cp -- .config/i3/lock.sh "$backup_dir/lock.sh"
cp -- .config/picom/lockscreen.frag "$backup_dir/lockscreen.frag"
printf 'Backup directory: %s\n' "$backup_dir"
```

## 2. Prepare your image

These commands use ImageMagick's `convert` utility. Change the first path to
your image. Keep the subject near the center: the badge will crop the corners.

```sh
image="$HOME/Pictures/my-avatar.png"

convert "$image" -auto-orient \
  -resize '256x256^' -gravity center -extent 256x256 \
  -background '#1e1e2e' -alpha remove -alpha off \
  "$HOME/.dotfiles/.config/i3/lockscreen-avatar.png"

convert -size 1920x1080 'xc:#1e1e2e' \
  "$HOME/.dotfiles/.config/i3/lockscreen-avatar.png" \
  -gravity northwest -geometry +0+0 -composite \
  "PNG24:$HOME/.dotfiles/.config/i3/lockscreen-image.png"
```

The first command creates the square image source. The second embeds it into a
full-screen, opaque PNG. Image conversion happens once during setup, rather than
when you lock or suspend.

The background must stay `#1e1e2e`, matching `BACKGROUND` in the shader.
The 256×256 source size must match `AVATAR_SIZE` below.

If the display layout changes, regenerate the canvas with the new total desktop
dimensions and reassess the source corner: no monitor's native password
indicator should overlap that 256×256 area. The ball remains centered on the
combined desktop. This recipe does not automatically adapt the canvas to hotplug
or DPI changes.

## 3. Give i3lock the PNG

Replace the contents of `.config/i3/lock.sh` with:

```sh
#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Keep exec and --nofork for xss-lock's suspend-readiness handshake.
image="$HOME/.config/i3/lockscreen-image.png"
if [ -r "$image" ]; then
    exec i3lock --nofork --color=1e1e2e --image="$image"
fi
exec i3lock --nofork --color=1e1e2e
```

Keep this file executable. Your existing bindings and xss-lock listener already
call this path, so their commands do not need changing.

The fallback handles a missing image file. If the PNG is corrupt, replace or
remove it before trying to lock again; a readable corrupt file still reaches
i3lock's image loader.

## 4. Teach the shader where to find the image

Edit `.config/picom/lockscreen.frag`. Keep `#version 330` as its first line.

After the existing `PURPLE` constant, add this constant and function:

```glsl
const float AVATAR_SIZE = 256.0;

vec3 avatar_color(vec2 image_uv) {
    // Pixel coordinates inside the PNG's top-left image-source patch.
    vec2 pixel = clamp(image_uv, vec2(0.0), vec2(1.0)) * (AVATAR_SIZE - 1.0);
    return texelFetch(tex, ivec2(pixel), 0).rgb;
}
```

At the start of `window_shader()`, find:

```glsl
if (distance(source.rgb, BACKGROUND) > 0.015) {
    return vec4(source.rgb, 1.0);
}
```

Replace that condition and its body with:

```glsl
bool image_patch = texcoord.x < AVATAR_SIZE && texcoord.y < AVATAR_SIZE;
if (!image_patch && distance(source.rgb, BACKGROUND) > 0.015) {
    return vec4(source.rgb, 1.0);
}
```

This hides the flat image-source patch behind the generated background while
preserving the actual password indicator elsewhere.

## 5. Replace the drawn padlock with the image badge

Inside the sphere-rendering block, keep the existing `longitude` calculation and
this line:

```glsl
vec2 emblem = vec2(longitude / 0.95, rotated.y * 1.25);
```

Immediately after it, replace everything from `float mark = ...` through
`mark *= ...` with:

```glsl
// A circular badge repeated on both sides of the rotating sphere.
vec2 image_uv = emblem / 1.44 + 0.5;
image_uv.y = 1.0 - image_uv.y;
float badge = 1.0 - smoothstep(0.70, 0.73, length(emblem));
vec3 image_color = avatar_color(image_uv);
```

Then replace:

```glsl
vec3 surface = mix(vec3(0.13, 0.11, 0.20), PURPLE * 0.85, mark);
```

with:

```glsl
vec3 surface = mix(vec3(0.13, 0.11, 0.20), image_color, badge);
```

Leave the remaining lighting, rim glow, edge smoothing, and final opaque return
unchanged. The old `lock_shape()` and `rounded_box()` functions can remain; they
will simply be unused.

The image will curve with the sphere and turn out of view near its sides. It is
a badge on a rotating surface, not a flat overlay that always faces you.

## 6. Reload and check

Confirm the asset is reachable through your live configuration path:

```sh
test -r "$HOME/.config/i3/lockscreen-image.png" && echo 'Image is linked'
sh -n "$HOME/.config/i3/lock.sh"
```

Your current i3/Picom configuration directories resolve into this repository.
If you later switch to individual Stow links, rerun the repository's documented
Stow command to link the new PNG files before proceeding.

Ask the existing Picom process to reload its configuration and shader:

```sh
pkill -USR1 -u "$(id -u)" -x picom
```

An i3 reload is unnecessary because the launcher path has not changed. Changes
to `lock.sh` take effect the next time it is executed.

Press **Super+L** and check that:

- Your picture rotates on the ball, with no flat picture in the top-left corner.
- Typing produces i3lock's normal password indicator and you can unlock normally.
- The background covers the whole screen, including its corners.

These image-mapping edits are instructions, not a configuration already tested
on your image. Check them before relying on the customized appearance.

## Adjustments and troubleshooting

- **Upside-down picture:** remove `image_uv.y = 1.0 - image_uv.y;` and reload.
- **Flat image visible in the corner:** check the `image_patch` exception and
  reload Picom. If Picom is stopped, the flat source image is expected: i3lock
  displays its PNG directly, while continuing to lock the screen normally.
- **Incorrect or empty picture:** verify both PNG paths and the 256×256 patch
  dimensions. Regenerate the canvas after changing the avatar.
- **Picture too dark:** reduce the lighting multiplier's effect by changing
  `surface *= 0.45 + 0.65 * diffuse;` to `surface *= 0.75 + 0.25 * diffuse;`.
- **Rotation speed:** change `seconds * 0.65`; a lower value turns more slowly.
- **Full globe wrap:** use an equirectangular texture and longitude/latitude UV
  mapping instead of the circular badge. That requires a different image layout;
  a square portrait will stretch when wrapped over the whole sphere.

## Roll back

In the terminal where you created the backup:

```sh
cp -- "$backup_dir/lock.sh" "$HOME/.dotfiles/.config/i3/lock.sh"
cp -- "$backup_dir/lockscreen.frag" "$HOME/.dotfiles/.config/picom/lockscreen.frag"
pkill -USR1 -u "$(id -u)" -x picom
```

If you opened another terminal, first set `backup_dir` to the backup directory
printed in step 1. The generated PNGs can remain on disk; the restored launcher
and shader do not use them.
