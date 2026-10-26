#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Launch an indexed XDG desktop entry through GIO, without parsing Exec ourselves."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def desktop_file(entry_id):
    wanted = entry_id if entry_id.endswith(".desktop") else entry_id + ".desktop"
    roots = [os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")]
    roots += (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    for root in roots:
        applications = Path(root) / "applications"
        for path in sorted(applications.rglob("*.desktop")):
            if str(path.relative_to(applications)).replace("/", "-") == wanted:
                return path
    raise FileNotFoundError(f"Application is no longer installed: {entry_id}")


def main():
    try:
        path = desktop_file(sys.argv[1])
        # GIO uses the system terminal handler for Terminal=true applications.
        if not shutil.which("gio"):
            raise RuntimeError("Install libglib2.0-bin to launch desktop applications.")
        result = subprocess.run(["gio", "launch", str(path)], check=False)
        return result.returncode
    except (IndexError, OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
