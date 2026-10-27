// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import Quickshell.I3
import Quickshell.Io

Item {
    id: root
    property string windowTitle: "Desktop"
    readonly property var workspaces: I3.workspaces.values
    function focusWorkspace(name): void { I3.dispatch("workspace " + JSON.stringify(String(name))); }
    function scrollWorkspace(direction): void { I3.dispatch(direction > 0 ? "workspace prev_on_output" : "workspace next_on_output"); }
    // Subscribe to title/focus changes; query once per burst, never poll the tree.
    I3IpcListener {
        subscriptions: ["window", "workspace"]
        onIpcEvent: titleDebounce.restart()
    }
    Timer {
        id: titleDebounce
        interval: 50
        onTriggered: {
            if (titleProcess.running)
                restart();
            else
                titleProcess.running = true;
        }
    }
    Process {
        id: titleProcess
        command: ["i3-msg", "-t", "get_tree"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                function focused(node) {
                    if (node.focused && node.window)
                        return node.name || "Untitled";
                    for (const child of (node.nodes || []).concat(node.floating_nodes || [])) {
                        const title = focused(child);
                        if (title !== null)
                            return title;
                    }
                    return null;
                }
                try {
                    root.windowTitle = focused(JSON.parse(text)) || "Desktop";
                } catch (error) {
                    root.windowTitle = "Desktop";
                }
            }
        }
    }

}
