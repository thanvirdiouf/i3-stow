# SPDX-License-Identifier: GPL-3.0-or-later
"""Group wheel events into gestures for the i3 and bspwm workspace bindings."""
from contextlib import contextmanager
import fcntl
import time


@contextmanager
def scroll_burst(state_path):
    """Yield True on the first event after 350 ms of quiet, holding the lock through the switch."""
    with state_path.open("a+") as state:
        fcntl.flock(state, fcntl.LOCK_EX)
        now = time.monotonic()
        state.seek(0)
        previous = state.read().strip()
        # Every wheel event extends the gesture, including suppressed events.
        state.seek(0)
        state.truncate()
        state.write(str(now))
        state.flush()
        yield not previous or now - float(previous) >= 0.35
