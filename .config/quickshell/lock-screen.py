#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render QML artwork, then exec the trusted X11 locker, keeping xss-lock's FD."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def screen_layout():
    result = subprocess.run(["xrandr", "--current"], capture_output=True, text=True,
                            check=True, timeout=2)
    size = re.search(r"current (\d+) x (\d+)", result.stdout)
    screens = []
    for line in result.stdout.splitlines():
        match = re.match(r"\S+ connected (?:primary )?(\d+)x(\d+)\+(\d+)\+(\d+)", line)
        if match:
            width, height, x, y = map(int, match.groups())
            rect = {"x": x, "y": y, "width": width, "height": height}
            if rect not in screens:
                screens.append(rect)
    if not size or not screens:
        raise RuntimeError("No active X11 monitor layout")
    return {"width": int(size[1]), "height": int(size[2]), "screens": screens}


def render(output, layout=None):
    env = os.environ.copy()
    env.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", QT_SCALE_FACTOR="1",
               QT_SCREEN_SCALE_FACTORS="", QT_SCALE_FACTOR_ROUNDING_POLICY="PassThrough",
               QS_LOCK_OUTPUT=str(output), QS_LOCK_LAYOUT=json.dumps(layout or screen_layout()))
    # Offscreen software rendering does not need nixGL or the session's GPU.
    subprocess.run(["quickshell", "--path", str(Path(__file__).with_name("lock-render.qml"))],
                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                   timeout=5, check=True)
    if not output.is_file() or output.stat().st_size < 100:
        raise RuntimeError("Quickshell did not render lockscreen artwork")


def cache_path():
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "quickshell" / "spectre-lock.png"


def update_cache():
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Render privately and publish atomically so locking never reads half a PNG.
    with tempfile.TemporaryDirectory(prefix=".lock-", dir=path.parent) as directory:
        image = Path(directory) / "lock.png"
        render(image)
        image.chmod(0o600)
        image.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", type=Path, help="Save artwork only; never lock (safe preview)")
    parser.add_argument("--update-cache", action="store_true", help="Refresh cached artwork; never lock")
    args = parser.parse_args()
    if args.render:
        render(args.render.resolve())
        return
    if args.update_cache:
        update_cache()
        return

    command = ["i3lock", "--nofork", "--color=282a36"]
    try:
        with tempfile.TemporaryDirectory(prefix="spectre-lock-") as directory:
            image = Path(directory) / "lock.png"
            if os.environ.get("XSS_SLEEP_LOCK_FD"):
                # Never spend logind's limited suspend-inhibit time rendering.
                # A missing cache falls back to solid i3lock immediately.
                image = cache_path()
            else:
                render(image)
            # Keep artwork anonymous after exec; no accumulating image files.
            image_fd = os.memfd_create("spectre-lock", flags=0)
            with os.fdopen(os.dup(image_fd), "wb") as target, image.open("rb") as source:
                shutil.copyfileobj(source, target)
            os.lseek(image_fd, 0, os.SEEK_SET)
            command += ["--image", f"/proc/self/fd/{image_fd}"]
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Lock artwork unavailable; using solid i3lock fallback: {error}", file=sys.stderr)

    # exec keeps the inherited descriptor open. i3lock itself releases the
    # suspend inhibitor after obtaining its keyboard/pointer grabs.
    sleep_fd = os.environ.get("XSS_SLEEP_LOCK_FD")
    if sleep_fd and sleep_fd.isdecimal():
        os.set_inheritable(int(sleep_fd), True)
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
