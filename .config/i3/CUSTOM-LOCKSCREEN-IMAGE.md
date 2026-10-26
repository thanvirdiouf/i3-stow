# Superman design on the spinning lock ball

The active i3lock/Picom lockscreen now uses the supplied `Superman2025Logo.jpg`
design. The shield rotates on both faces of the purple ball. Its red/gold colors
are retained, while the shader keys out the photo's blue backdrop. i3lock still
owns authentication, keyboard/pointer grabs, and password feedback.

## Active files

- `lock.sh` passes `lockscreen-image.png` to `i3lock --nofork`.
- `lockscreen-avatar.png` is a 256×256 texture containing the complete shield.
- `lockscreen-image.png` is an opaque **1920×1080** canvas with that texture in
  its top-left 256×256 corner, plus two marker pixels.
- `../picom/lockscreen.frag` samples the texture and maps it onto the ball.

Picom gets only the lock window's texture; it does not load a separate image.
The top-left patch carries the image into the shader, which hides the flat
source and renders the shield on the sphere instead. Purple and cyan marker
pixels at `(0,0)` and `(1,0)` identify image mode. Without them, the same shader
renders the original procedural purple padlock.

The source patch is away from the native password indicator on this machine's
single 1920×1080 layout. While typing, the ball stays inside i3lock's green
ring instead of being covered by its dark disk. Backspace highlights, status
rings, authentication text, and Caps Lock notices remain visible over the ball.
Only the native disk's flat fills are replaced within the ball; other feedback
pixels are preserved. Without Picom, i3lock still
secures the screen, but its source image is visible in the top-left corner.

## Rebuild the assets

These commands use ImageMagick, preserve the whole image's aspect ratio, and
leave the original JPEG untouched. Run from the repository root:

```sh
image="$HOME/Downloads/Superman2025Logo.jpg"

convert "$image" -auto-orient -resize 224x224 \
  -background '#1e1e2e' -gravity center -extent 256x256 \
  -alpha remove -alpha off PNG24:.config/i3/lockscreen-avatar.png

convert -size 1920x1080 'xc:#1e1e2e' \
  .config/i3/lockscreen-avatar.png \
  -gravity northwest -geometry +0+0 -composite \
  -fill '#bd93f9' -draw 'point 0,0' \
  -fill '#8be9fd' -draw 'point 1,0' \
  PNG24:.config/i3/lockscreen-image.png
```

If the display layout changes, rebuild the canvas to match the total desktop
size and check that no monitor's native password indicator overlaps the source
patch. The ball remains centered on the combined desktop. No conversion runs
during locking or suspend, so the xss-lock readiness handoff stays immediate.

If using individual Stow links, rerun the documented Stow command to link the
new PNGs. The current i3 directory symlink already exposes both files.

## Customize or disable

- Change `seconds * 0.65` in the shader to change rotation speed.
- Adjust `emblem / 1.8` to change the shield's size on the sphere.
- The blue-background key is tailored to this image. For a different photo,
  adjust or remove `blue_background` in the shader.
- Move `lockscreen-image.png` aside to restore the original purple padlock.
  No shader edit is needed. The wrapper's solid-color fallback is automatic.
- Keep `--color=1e1e2e` synchronized with the shader's `BACKGROUND` constant.

Reload Picom after shader changes:

```sh
pkill -USR1 -u "$(id -u)" -x picom
```

The shader was compiled and rendered in an invisible GLX buffer on the desktop's
Intel GPU at multiple rotation angles. Cairo fixtures modeled stock i3lock
2.14.1 typing, backspace, verifying, and wrong-password states. The typing-state
logo center matched the idle render exactly, and solid native ring/separator
pixels and black message pixels were preserved exactly. A second typing frame
confirmed the ball still rotates. The disk-fill colors follow
[upstream i3lock 2.14.1](https://github.com/i3/i3lock/blob/2.14.1/unlock_indicator.c);
custom i3lock builds may require matching their own fill colors.
A real lock or suspend was not triggered during these checks.

## Artwork provenance

The texture was derived from the user-supplied
`/home/spectre/Downloads/Superman2025Logo.jpg`. The Superman artwork belongs to its
respective rights holders and is not covered by this repository's code license.
