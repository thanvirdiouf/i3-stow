// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import Quickshell
import Quickshell.Io

Item {
    id: root
    property string windowTitle: "Desktop"
    property var workspaces: []
    property var reservations: ({})
    function reserveSpace(monitor, height): void {
        reservations[monitor] = height;
        if (events.running)
            events.write(JSON.stringify({ monitor: monitor, height: height }) + "\n");
    }
    function focusWorkspace(name): void { Quickshell.execDetached(["bspc", "desktop", "-f", String(name)]); }
    function scrollWorkspace(direction): void {
        Quickshell.execDetached(["python3", Quickshell.shellPath("../bspwm/actions.py"), "scroll", direction > 0 ? "prev" : "next"]);
    }
    Process {
        id: events
        command: ["python3", Quickshell.shellPath("bspwm-state.py")]
        running: true
        stdinEnabled: true
        onStarted: {
            for (const monitor of Object.keys(root.reservations))
                root.reserveSpace(monitor, root.reservations[monitor]);
        }
        stdout: SplitParser {
            onRead: data => {
                try {
                    const state = JSON.parse(data);
                    root.workspaces = state.workspaces;
                    root.windowTitle = state.title;
                } catch (error) { console.warn("Invalid bspwm state:", error); }
            }
        }
        onExited: retry.restart()
    }
    Timer { id: retry; interval: 1000; onTriggered: events.running = true }
}
