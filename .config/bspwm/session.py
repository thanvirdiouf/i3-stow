#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Own session daemons per display, including across config reloads/restarts."""
import fcntl
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def main():
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
    display = os.environ.get('DISPLAY', 'default').replace('/', '_')
    with (runtime / f'spectre-bspwm-{os.getuid()}-{display}.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
        env = dict(os.environ, XDG_CURRENT_DESKTOP='bspwm', SPECTRE_WM='bspwm')
        children = []
        commands = [
            ['python3', str(config / 'bspwm/monitors.py')],
            ['sh', str(config / 'sxhkd/start.sh')],
            ['sh', str(config / 'picom/start.sh')],
            ['nixGL', 'quickshell', '--no-duplicate'],
            ['xss-lock', '--transfer-sleep-lock', '--', str(config / 'i3/lock.sh')],
            ['nm-applet'], ['kdeconnect-indicator'],
            ['/usr/lib/policykit-1-gnome/polkit-gnome-authentication-agent-1'],
            ['dex', '--autostart', '--environment', 'bspwm'],
            ['feh', '--bg-fill', str(config / 'i3/wall.jpg')],
        ]
        def stop(*_):
            raise SystemExit()

        signal.signal(signal.SIGTERM, stop)
        try:
            with (runtime / f'spectre-bspwm-{os.getuid()}-{display}.log').open('a') as log:
                for command in commands:
                    if shutil.which(command[0]):
                        children.append(subprocess.Popen(command, env=env, stdout=log, stderr=log,
                                                         start_new_session=True))
                failures = 0
                while failures < 3:
                    time.sleep(1)
                    connected = subprocess.run(['bspc', 'query', '-M'], stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL).returncode == 0
                    failures = 0 if connected else failures + 1
        finally:
            for child in children:
                if child.poll() is None:
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass


if __name__ == '__main__':
    main()
