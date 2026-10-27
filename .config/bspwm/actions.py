#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small UX operations that need more context than a single bspc command."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def bsp(*args, check=True):
    return subprocess.run(['bspc', *args], check=check, capture_output=True, text=True).stdout.strip()


def desktops():
    """Keep global names 1..10, distributing them only on first setup."""
    world = json.loads(bsp('wm', '-d'))
    monitors = world['monitors']
    existing = {d['name'] for m in monitors for d in m['desktops']}
    for index in range(1, 11):
        name = str(index)
        if name not in existing:
            monitor = monitors[min((index - 1) * len(monitors) // 10, len(monitors) - 1)]
            bsp('monitor', str(monitor['id']), '-a', name)
    # Drop only unused default desktops. Never reset/rename live desktops on reload.
    for monitor in monitors:
        for desktop in monitor['desktops']:
            if desktop['name'] == 'Desktop' and desktop['root'] is None:
                bsp('desktop', str(desktop['id']), '-r', check=False)


def scroll(direction):
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
    display = os.environ.get('DISPLAY', 'default').replace('/', '_')
    with (runtime / f'bspwm-scroll-{os.getuid()}-{display}').open('a+') as state:
        fcntl.flock(state, fcntl.LOCK_EX)
        state.seek(0)
        previous = state.read()
        now = time.monotonic()
        state.seek(0)
        state.truncate()
        state.write(str(now))
        state.flush()
        if not previous or now - float(previous) >= .35:
            bsp('desktop', '-f', f'{direction}.local', check=False)


def resize(direction):
    # Try the outside edge, then the opposite edge for tiles at the screen edge.
    handles = {'west': [('left', '-40', '0'), ('right', '-40', '0')],
               'east': [('right', '40', '0'), ('left', '40', '0')],
               'north': [('top', '0', '-40'), ('bottom', '0', '-40')],
               'south': [('bottom', '0', '40'), ('top', '0', '40')]}
    for handle in handles[direction]:
        result = subprocess.run(['bspc', 'node', '-z', *handle], capture_output=True)
        if result.returncode == 0:
            break


def main():
    action, *args = sys.argv[1:]
    if action == 'desktops':
        desktops()
    elif action == 'scroll':
        scroll(args[0])
    elif action == 'resize':
        resize(args[0])
    elif action == 'focus-mode':
        current = json.loads(bsp('query', '-T', '-n', 'focused'))
        state = current.get('client', {}).get('state')
        selector = 'any.local.tiled' if state == 'floating' else 'any.local.floating'
        bsp('node', '-f', selector, check=False)
    elif action == 'scheme':
        scheme = bsp('config', 'automatic_scheme')
        bsp('config', 'automatic_scheme', 'alternate' if scheme == 'longest_side' else 'longest_side')
    elif action == 'reload':
        subprocess.run(['sh', str(Path(__file__).with_name('bspwmrc'))], check=True)
        if os.environ.get('SXHKD_PID'):
            import signal
            os.kill(int(os.environ['SXHKD_PID']), signal.SIGUSR1)
    elif action == 'logout':
        answer = subprocess.run(['rofi', '-dmenu', '-p', 'Log out of bspwm?'],
                                input='No\nYes\n', text=True, capture_output=True).stdout.strip()
        if answer == 'Yes':
            bsp('quit')
    else:
        raise SystemExit('Unknown bspwm action')


if __name__ == '__main__':
    main()
