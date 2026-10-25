#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Forward clicks to SNI items that expose native XEmbed menus, not DBusMenu."""

import json
import subprocess
import sys

INTERFACE = "org.kde.StatusNotifierItem"


def property_value(service, path, interface, name):
    result = subprocess.run(
        ["busctl", "--user", "--json=short", "get-property", service, path, interface, name],
        check=True, capture_output=True, text=True, timeout=2,
    )
    return json.loads(result.stdout)["data"]


def main():
    if len(sys.argv) != 5 or sys.argv[2] not in {"Activate", "SecondaryActivate", "ContextMenu"}:
        raise ValueError("Expected ITEM_ID ACTION X Y")
    item_id, action = sys.argv[1:3]
    x, y = (str(int(value)) for value in sys.argv[3:5])
    items = property_value(
        "org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher",
        "org.kde.StatusNotifierWatcher", "RegisteredStatusNotifierItems",
    )
    for item in items:
        service, separator, suffix = item.partition("/")
        path = "/" + suffix if separator else "/StatusNotifierItem"
        try:
            candidate = property_value(service, path, INTERFACE, "Id")
        except (subprocess.SubprocessError, KeyError, ValueError):
            continue  # An app may disappear while the menu is opening.
        if candidate == item_id:
            subprocess.run(
                ["busctl", "--user", "call", service, path, INTERFACE, action, "ii", x, y],
                check=True, timeout=3,
            )
            return
    raise ValueError(f"Tray item disappeared: {item_id}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.SubprocessError, KeyError, ValueError) as error:
        print(f"Tray action failed: {error}", file=sys.stderr)
        sys.exit(1)
