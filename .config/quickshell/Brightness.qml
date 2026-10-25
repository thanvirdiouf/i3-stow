// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root
    // The external display uses the same serialized DDC helper as Polybar.
    required property bool external
    property int percentage: -1
    readonly property string helper: Quickshell.shellPath("../polybar/monitor-brightness.sh")
    property int pendingSteps: 0

    function refresh() {
        if (!readProcess.running && !writeProcess.running)
            readProcess.running = true;
    }

    function adjust(direction) {
        pendingSteps += direction;
        applyPending();
    }

    function applyPending() {
        if (writeProcess.running || readProcess.running || pendingSteps === 0)
            return;
        const direction = pendingSteps > 0 ? 1 : -1;
        pendingSteps -= direction;
        writeProcess.command = external ? ["bash", helper, direction > 0 ? "up" : "down"] : ["brightnessctl", "--class=backlight", "--min-value=1", "set", direction > 0 ? "+5%" : "5%-"];
        writeProcess.running = true;
    }

    Process {
        id: readProcess
        command: root.external ? ["bash", root.helper] : ["brightnessctl", "--class=backlight", "--machine-readable"]

        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                const value = root.external ? text.trim() : (text.trim().split(",")[3] || "").replace("%", "");
                root.percentage = /^\d+$/.test(value) ? Math.min(100, Number(value)) : -1;
            }
        }
        stderr: StdioCollector {}
        onExited: exitCode => {
            if (exitCode !== 0)
                root.percentage = -1;
            root.applyPending();
        }
    }

    Process {
        id: writeProcess
        stdout: StdioCollector {}
        stderr: StdioCollector {}
        onExited: {
            if (root.pendingSteps !== 0)
                root.applyPending();
            else
                root.refresh();
        }
    }

    Timer {
        interval: 15000
        running: true
        repeat: true
        onTriggered: root.refresh()
    }
}
