#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# See COPYING.md in the repository root for the license text.
"""Switch once per scroll burst; reset after a quiet interval."""

import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".local/lib"))
from workspace_scroll import scroll_burst


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("next", "prev"):
        raise SystemExit("Usage: workspace-scroll.py next|prev")

    state_dir = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / (
        f"i3-workspace-scroll-{os.getuid()}"
    )
    state_dir.mkdir(mode=0o700, exist_ok=True)
    with scroll_burst(state_dir / "last-event") as first_event:
        if first_event:
            subprocess.run(
                ["i3-msg", "workspace", f"{sys.argv[1]}_on_output"],
                check=True,
                stdout=subprocess.DEVNULL,
            )


if __name__ == "__main__":
    main()
