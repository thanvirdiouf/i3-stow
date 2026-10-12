#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# See COPYING.md in the repository root for the license text.
"""Dwindle-style autotiling for i3, using only Python's standard library."""

import fcntl
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import time

HEADER = struct.Struct("=6sII")
MAGIC = b"i3-ipc"
EVENT = 1 << 31


def receive_exact(connection, size):
    data = bytearray()
    while len(data) < size:
        chunk = connection.recv(size - len(data))
        if not chunk:
            raise ConnectionError("i3 disconnected")
        data.extend(chunk)
    return bytes(data)


def receive(connection):
    magic, size, kind = HEADER.unpack(receive_exact(connection, HEADER.size))
    if magic != MAGIC:
        raise ConnectionError("Invalid i3 IPC header")
    return kind, json.loads(receive_exact(connection, size))


def send(connection, kind, payload=""):
    data = payload.encode()
    connection.sendall(HEADER.pack(MAGIC, len(data), kind) + data)


def request(connection, kind, payload=""):
    send(connection, kind, payload)
    reply_kind, reply = receive(connection)
    if reply_kind != kind:
        raise ConnectionError("Unexpected i3 IPC reply")
    return reply


def focused_path(node, ancestors=()):
    if node.get("focused"):
        return (*ancestors, node)
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        result = focused_path(child, (*ancestors, node))
        if result:
            return result
    return ()


def split_command(tree):
    path = focused_path(tree)
    if len(path) < 2:
        return None
    leaf, parent = path[-1], path[-2]
    # Respect floating windows, manually selected groups, tabs and stacks.
    if not leaf.get("window") or leaf.get("nodes"):
        return None
    if any(
        node.get("type") == "floating_con"
        or node.get("floating") in ("auto_on", "user_on")
        or node.get("layout") in ("tabbed", "stacked")
        or (node.get("type") == "con" and node.get("fullscreen_mode", 0))
        for node in path
    ):
        return None
    rect = leaf["rect"]
    if not rect["width"] or not rect["height"]:
        return None
    direction = "h" if rect["width"] >= rect["height"] else "v"
    layout = "split" + direction
    if parent.get("layout") == layout and len(parent.get("nodes", [])) == 1:
        return None  # Already prepared; avoid repeatedly creating containers.
    selector = f'[con_id={leaf["id"]}]'
    if parent.get("layout") == layout:
        # Same-axis split normally adds a sibling. Wrap the leaf first so only
        # its space is divided, even on very wide monitors or after resizing.
        opposite = "v" if direction == "h" else "h"
        return f"{selector} split {opposite}; {selector} split {direction}"
    return f"{selector} split {direction}"


def prepare(connection):
    command = split_command(request(connection, 4))  # GET_TREE
    if command:
        for result in request(connection, 0, command):
            if not result.get("success"):
                print(f"dwindle: {result.get('error', 'split failed')}", file=sys.stderr)


def socket_path():
    # Rediscover after a restart rather than trusting a stale I3SOCK value.
    return subprocess.check_output(["i3", "--get-socketpath"], text=True).strip()


def listen(path, enabled):
    with socket.socket(socket.AF_UNIX) as commands, socket.socket(socket.AF_UNIX) as events:
        commands.settimeout(5)
        commands.connect(path)
        events.connect(path)
        send(events, 2, json.dumps(["window", "workspace", "output", "tick", "shutdown"]))
        # Events may arrive before the subscription reply.
        while True:
            kind, reply = receive(events)
            if kind == 2:
                if not reply.get("success"):
                    raise ConnectionError("i3 rejected event subscription")
                break
        if enabled:
            prepare(commands)
        while True:
            kind, event = receive(events)
            if kind == EVENT | 6:  # Shutdown
                return enabled, event.get("change") == "exit"
            if kind == EVENT | 7:
                if event.get("payload") != "dwindle-toggle":
                    continue
                enabled = not enabled
                print(f"dwindle: {'enabled' if enabled else 'disabled'}", flush=True)
            elif kind == EVENT | 3:
                if event.get("change") not in (
                    "focus", "new", "close", "move", "floating", "fullscreen_mode"
                ):
                    continue
            elif kind == EVENT | 0:
                if event.get("change") not in ("focus", "init", "reload", "restored"):
                    continue
            elif kind != EVENT | 1:
                continue
            if enabled:
                prepare(commands)


def main():
    # DISPLAY stays stable across restarts, unlike the socket's PID suffix.
    display = os.environ.get("DISPLAY", "default").replace("/", "_")
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
    lock_path = runtime / f"i3-dwindle-{os.getuid()}-{display}.lock"
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        enabled = True
        while True:
            try:
                enabled, exiting = listen(socket_path(), enabled)
                if exiting:
                    return
            except (OSError, ValueError, subprocess.CalledProcessError) as error:
                print(f"dwindle: reconnecting: {error}", file=sys.stderr, flush=True)
            time.sleep(1)


if __name__ == "__main__":
    main()
