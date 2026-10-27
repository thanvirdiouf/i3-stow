#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Name desktops on monitors that arrive after bspwm's initial config."""
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import time

from actions import desktops


def main():
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
    display = os.environ.get('DISPLAY', 'default').replace('/', '_')
    with (runtime / f'bspwm-monitors-{os.getuid()}-{display}.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return

        def stop(*_):
            raise SystemExit()

        signal.signal(signal.SIGTERM, stop)
        failures = 0
        while failures < 3:
            events = subprocess.Popen(['bspc', 'subscribe', 'monitor_add', 'monitor_remove'],
                                      stdout=subprocess.PIPE, text=True)
            try:
                desktops()
                for _ in events.stdout:
                    desktops()
                    failures = 0
            except (subprocess.SubprocessError, OSError, ValueError) as error:
                print(f'bspwm monitors: {error}', flush=True)
            finally:
                events.terminate()
                events.wait()
            failures += 1
            time.sleep(1)


if __name__ == '__main__':
    main()
