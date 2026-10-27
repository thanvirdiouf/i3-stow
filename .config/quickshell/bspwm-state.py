#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bspwm events to a small JSON model; title changes refreshed once a second."""
import json
import os
import select
import signal
import subprocess
import sys


def leaves(node):
    if not node:
        return []
    if node.get('client'):
        return [node]
    return leaves(node.get('firstChild')) + leaves(node.get('secondChild'))


def model(world):
    workspaces = []
    focused = 0
    for monitor in world['monitors']:
        for desktop in monitor['desktops']:
            nodes = leaves(desktop.get('root'))
            name = desktop['name']
            workspaces.append(dict(name=name, number=int(name) if name.isdigit() else -1,
                                   active=desktop['id'] == monitor['focusedDesktopId'],
                                   occupied=bool(nodes), urgent=any(n['client'].get('urgent', False) for n in nodes),
                                   monitor=dict(name=monitor['name'])))
            if monitor['id'] == world['focusedMonitorId'] and desktop['id'] == monitor['focusedDesktopId']:
                focused = desktop.get('focusedNodeId', 0)
    return dict(workspaces=workspaces), focused


def snapshot():
    result = subprocess.run(['bspc', 'wm', '-d'], text=True, capture_output=True, check=True, timeout=2)
    state, focused = model(json.loads(result.stdout))
    title = 'Desktop'
    if focused:
        result = subprocess.run(['xprop', '-notype', '-id', str(focused), '_NET_WM_NAME', 'WM_NAME'],
                                text=True, capture_output=True, timeout=2)
        for line in result.stdout.splitlines():
            if ' = "' in line:
                raw = line.split(' = ', 1)[1]
                try:
                    title = json.loads(raw)
                except ValueError:
                    title = raw.strip('"')
                break
    state['title'] = title
    return json.dumps(state, ensure_ascii=False)


def main():
    def stop(*_):
        raise SystemExit()

    signal.signal(signal.SIGTERM, stop)
    # Binary nonblocking reads avoid text buffering swallowing pending events.
    events = subprocess.Popen(['bspc', 'subscribe', 'report'], stdout=subprocess.PIPE)
    # Clear stale padding after a shell restart; every bar starts hidden.
    world = json.loads(subprocess.check_output(['bspc', 'wm', '-d'], text=True))
    for monitor in world['monitors']:
        subprocess.run(['bspc', 'config', '-m', monitor['name'], 'top_padding', '0'], check=True)
    inputs = [events.stdout, sys.stdin]
    pending = b''
    previous = None
    try:
        while True:
            current = snapshot()
            if current != previous:
                print(current, flush=True)
                previous = current
            ready, _, _ = select.select(inputs, [], [], 1)
            if events.stdout in ready and not os.read(events.stdout.fileno(), 65536):
                break
            if sys.stdin in ready:
                data = os.read(sys.stdin.fileno(), 65536)
                if not data:
                    inputs.remove(sys.stdin)
                    continue
                pending += data
                updates = {}
                while b'\n' in pending:
                    line, pending = pending.split(b'\n', 1)
                    update = json.loads(line)
                    updates[update['monitor']] = max(0, min(200, int(update['height'])))
                for monitor, height in updates.items():
                    subprocess.run(['bspc', 'config', '-m', monitor, 'top_padding', str(height)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'bspwm state: {error}', file=sys.stderr)
    finally:
        for monitor in world['monitors']:
            subprocess.run(['bspc', 'config', '-m', monitor['name'], 'top_padding', '0'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        events.terminate()
        events.wait()


if __name__ == '__main__':
    main()
