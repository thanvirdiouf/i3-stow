#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Hold logind and X11 inhibitors while the Rofi wake-lock service runs."""
import ctypes
import ctypes.util
import os
import select
import socket
import sys

import dbus


def main():
    x11 = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
    xss = ctypes.CDLL(ctypes.util.find_library("Xss") or "libXss.so.1")
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x11.XConnectionNumber.argtypes = [ctypes.c_void_p]
    x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
    xss.XScreenSaverQueryVersion.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
    ]
    xss.XScreenSaverSuspend.argtypes = [ctypes.c_void_p, ctypes.c_int]

    display = x11.XOpenDisplay(None)
    if not display:
        raise RuntimeError("Cannot enable wake lock without an X11 display")
    inhibitor = None
    try:
        major, minor = ctypes.c_int(), ctypes.c_int()
        if not xss.XScreenSaverQueryVersion(display, ctypes.byref(major), ctypes.byref(minor)):
            raise RuntimeError("X11 screen saver extension is unavailable")
        if (major.value, minor.value) < (1, 1):
            raise RuntimeError("Wake lock requires X11 screen saver extension 1.1")

        manager = dbus.Interface(
            dbus.SystemBus().get_object("org.freedesktop.login1", "/org/freedesktop/login1"),
            "org.freedesktop.login1.Manager",
        )
        inhibitor = manager.Inhibit(
            "idle:sleep", "Rofi", "Power menu wake lock enabled", "block"
        ).take()
        # The X server releases this per-client suspension on disconnect.
        # This also suppresses DPMS without changing the user's timeouts.
        xss.XScreenSaverSuspend(display, True)
        x11.XSync(display, False)
        notify_socket = os.environ["NOTIFY_SOCKET"]
        if notify_socket.startswith("@"):
            notify_socket = "\0" + notify_socket[1:]
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notify:
            notify.sendto(b"READY=1", notify_socket)

        # Stop blocking sleep if the X server closes the display connection.
        display_events = select.poll()
        display_events.register(x11.XConnectionNumber(display), select.POLLHUP | select.POLLERR)
        display_events.poll()
    finally:
        x11.XCloseDisplay(display)
        if inhibitor is not None:
            os.close(inhibitor)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, dbus.DBusException) as error:
        print(f"Wake lock failed: {error}", file=sys.stderr)
        sys.exit(1)
