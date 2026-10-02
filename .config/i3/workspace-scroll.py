#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# See COPYING.md in the repository root for the license text.
"""Switch once per scroll burst; reset after a quiet interval."""

import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time

# Increase this if your touchpad's momentum events have longer gaps.
QUIET_SECONDS = 0.35


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("next", "prev"):
        raise SystemExit("Usage: workspace-scroll.py next|prev")

    state_dir = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / (
        f"i3-workspace-scroll-{os.getuid()}"
    )
    state_dir.mkdir(mode=0o700, exist_ok=True)
    with (state_dir / "last-event").open("a+") as state:
        # Serialize helpers launched by successive wheel events.
        fcntl.flock(state, fcntl.LOCK_EX)
        now = time.monotonic()
        state.seek(0)
        previous = state.read().strip()
        last_event = float(previous) if previous else None
        # Update even for suppressed events, so momentum extends the gesture.
        state.seek(0)
        state.truncate()
        state.write(str(now))
        state.flush()
        if last_event is None or now - last_event >= QUIET_SECONDS:
            subprocess.run(
                ["i3-msg", "workspace", f"{sys.argv[1]}_on_output"],
                check=True,
                stdout=subprocess.DEVNULL,
            )


if __name__ == "__main__":
    main()
