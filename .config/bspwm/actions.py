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
    # Re-query after additions. A hotplugged monitor may have only Desktop;
    # bspwm cannot remove its last desktop, so reuse a free numbered slot.
    world = json.loads(bsp('wm', '-d'))
    defaults = [d['id'] for m in world['monitors'] for d in m['desktops']
                if d['name'] == 'Desktop']
    for desktop_id in defaults:
        world = json.loads(bsp('wm', '-d'))
        owner = next(m for m in world['monitors'] if any(d['id'] == desktop_id for d in m['desktops']))
        desktop = next(d for d in owner['desktops'] if d['id'] == desktop_id)
        if desktop['root'] is None and len(owner['desktops']) > 1:
            bsp('desktop', str(desktop_id), '-r')
            continue
        free = next(((m, d) for m in world['monitors'] for d in m['desktops']
                     if d['name'] == '10'
                     and d['root'] is None and len(m['desktops']) > 1), None)
        if free:
            _, replacement = free
            # Removing an empty slot and renaming preserves all live trees,
            # including windows already opened on the default desktop.
            bsp('desktop', str(replacement['id']), '-r')
            bsp('desktop', str(desktop_id), '-n', replacement['name'])
        else:
            # Never steal an occupied workspace or leave a monitor without one.
            names = {d['name'] for m in world['monitors'] for d in m['desktops']}
            number = next(n for n in range(11, len(names) + 12) if str(n) not in names)
            bsp('desktop', str(desktop_id), '-n', str(number))


def occupied_target(world, direction):
    """Cycle occupied desktops on the focused monitor, including from an empty one."""
    monitor = next(m for m in world['monitors'] if m['id'] == world['focusedMonitorId'])
    desktops = monitor['desktops']

    def occupied(node):
        if not node or node.get('hidden', False):
            return False
        if node.get('client') is not None:
            return True
        return occupied(node.get('firstChild')) or occupied(node.get('secondChild'))

    current = next(i for i, d in enumerate(desktops) if d['id'] == monitor['focusedDesktopId'])
    step = -1 if direction == 'prev' else 1
    for distance in range(1, len(desktops)):
        desktop = desktops[(current + step * distance) % len(desktops)]
        if occupied(desktop['root']):
            return str(desktop['id'])
    return None


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
            target = occupied_target(json.loads(bsp('wm', '-d')), direction)
            if target:
                bsp('desktop', '-f', target, check=False)


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
