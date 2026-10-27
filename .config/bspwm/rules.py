#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""External rules allow case-insensitive app matching without global wildcards."""
import re
import subprocess
import sys

FLOATING = re.compile(r"^(localsend(_app)?|org\.localsend\.localsend_app|gedit|org\.gnome\.gedit|blueman-manager|pavucontrol|kdeconnect([._-].*)?|org\.kde\.kdeconnect([.-].*)?)$", re.I)


def consequences(class_name, title):
    if title in ("Spectre · Applications", "Spectre · System Monitor"):
        return "state=floating center=on border=off"
    if FLOATING.fullmatch(class_name):
        return "state=floating center=on"
    return ""


if __name__ == "__main__":
    subprocess.run(['xprop', '-id', sys.argv[1], '-f', '_SPECTRE_BSPWM', '32c',
                    '-set', '_SPECTRE_BSPWM', '1'], capture_output=True, timeout=2)
    title = subprocess.run(["xprop", "-id", sys.argv[1], "_NET_WM_NAME", "WM_NAME"],
                           capture_output=True, text=True, timeout=2).stdout
    title = next((line.split(' = ', 1)[1].strip('"') for line in title.splitlines()
                  if ' = ' in line), '')
    print(consequences(sys.argv[2], title))
