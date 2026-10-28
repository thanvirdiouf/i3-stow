#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Observe both Super keys on X11 without grabbing shortcuts used by other apps.

Runs only while the switcher is open. Querying key state also handles a quick
Super+Tab whose Super release precedes the asynchronous IPC/window-map operation.
"""
import ctypes
import ctypes.util
import time


def held(keymap, keycodes):
    return any(code and keymap[code // 8] & (1 << (code % 8)) for code in keycodes)


def main():
    x11 = ctypes.CDLL(ctypes.util.find_library('X11'))
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XKeysymToKeycode.restype = ctypes.c_ubyte
    x11.XQueryKeymap.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = x11.XOpenDisplay(None)
    if not display:
        raise SystemExit('Cannot observe Super keys without an X11 display')
    try:
        keys = [x11.XKeysymToKeycode(display, key) for key in (0xffeb, 0xffec)]
        keymap = (ctypes.c_ubyte * 32)()
        while True:
            x11.XQueryKeymap(display, keymap)
            if not held(keymap, keys):
                print('released', flush=True)
                return
            time.sleep(.02)
    finally:
        x11.XCloseDisplay(display)


if __name__ == '__main__':
    main()
