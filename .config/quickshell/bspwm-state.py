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
    recency = {entry['desktopId']: index for index, entry in enumerate(world.get('focusHistory', []))}
    for monitor in world['monitors']:
        for desktop in monitor['desktops']:
            nodes = leaves(desktop.get('root'))
            name = desktop['name']
            rect = monitor.get('rectangle', dict(x=0, y=0, width=1920, height=1080))
            windows = []
            for node in nodes:
                if node.get('hidden', False):
                    continue
                client = node['client']
                geometry = client.get('floatingRectangle' if client.get('state') == 'floating' else 'tiledRectangle',
                                      node.get('rectangle', rect))
                if client.get('state') == 'fullscreen':
                    geometry = rect
                windows.append(dict(app=client.get('className') or 'Window',
                                    x=(geometry['x'] - rect['x']) / max(1, rect['width']),
                                    y=(geometry['y'] - rect['y']) / max(1, rect['height']),
                                    width=geometry['width'] / max(1, rect['width']),
                                    height=geometry['height'] / max(1, rect['height'])))
            workspaces.append(dict(name=name, number=int(name) if name.isdigit() else -1,
                                   active=desktop['id'] == monitor['focusedDesktopId'],
                                   focused=monitor['id'] == world['focusedMonitorId'] and desktop['id'] == monitor['focusedDesktopId'],
                                   recency=recency.get(desktop['id'], -1), windows=windows,
                                   occupied=bool(windows), urgent=any(n['client'].get('urgent', False) for n in nodes),
                                   monitor=dict(name=monitor['name'])))
            if monitor['id'] == world['focusedMonitorId'] and desktop['id'] == monitor['focusedDesktopId']:
                focused = desktop.get('focusedNodeId', 0)
    return dict(workspaces=workspaces), focused


def snapshot(world):
    state, focused = model(world)
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

    bar_height = int(sys.argv[1])
    signal.signal(signal.SIGTERM, stop)
    # Binary nonblocking reads avoid text buffering swallowing pending events.
    events = subprocess.Popen(['bspc', 'subscribe', 'report'], stdout=subprocess.PIPE)
    monitors = []
    previous = None
    try:
        while True:
            world = json.loads(subprocess.check_output(['bspc', 'wm', '-d'], text=True, timeout=2))
            monitors = world['monitors']
            for monitor in monitors:
                if monitor['padding']['top'] != bar_height:
                    subprocess.run(['bspc', 'config', '-m', monitor['name'], 'top_padding', str(bar_height)],
                                   check=False, stderr=subprocess.DEVNULL)
            current = snapshot(world)
            if current != previous:
                print(current, flush=True)
                previous = current
            ready, _, _ = select.select([events.stdout], [], [], 1)
            if ready and not os.read(events.stdout.fileno(), 65536):
                break
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'bspwm state: {error}', file=sys.stderr)
    finally:
        for monitor in monitors:
            subprocess.run(['bspc', 'config', '-m', monitor['name'], 'top_padding', '0'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        events.terminate()
        events.wait()


if __name__ == '__main__':
    main()
