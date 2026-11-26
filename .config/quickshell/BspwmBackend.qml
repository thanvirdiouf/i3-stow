// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import Quickshell
import Quickshell.Io

Item {
    id: root
    property string windowTitle: "Desktop"
    property var workspaces: []
    function focusWorkspace(name): void { Quickshell.execDetached(["bspc", "desktop", "-f", String(name)]); }
    function scrollWorkspace(direction): void {
        Quickshell.execDetached([Quickshell.shellPath("../bspwm/native.sh"), "scroll", direction > 0 ? "prev" : "next"]);
    }
    Process {
        id: events
        command: ["python3", Quickshell.shellPath("bspwm-state.py"), String(Theme.barHeight)]
        running: true
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
