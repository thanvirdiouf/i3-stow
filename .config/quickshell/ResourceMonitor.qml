// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io

DesktopWindow {
    id: root
    title: "Spectre · System Monitor"
    implicitWidth: 760
    implicitHeight: 690
    property var stats: null
    property var cpuHistory: []
    property var memoryHistory: []
    property var diskHistory: []
    property var netHistory: []
    property string status: "Connecting to system…"

    function bytes(value) {
        const units = ["B", "KiB", "MiB", "GiB", "TiB"];
        let i = 0;
        while (value >= 1024 && i < units.length - 1) {
            value /= 1024;
            ++i;
        }
        return value.toFixed(i > 1 ? 1 : 0) + " " + units[i];
    }
    function record(history, value) {
        return history.concat([value]).slice(-45);
    }
    function open() {
        visible = true;
    }

    Process {
        id: sampler
        command: ["python3", Quickshell.shellPath("resources.py")]
        running: root.visible
        stdout: SplitParser {
            onRead: line => {
                try {
                    root.stats = JSON.parse(line);
                    root.status = "Live · 2 s refresh";
                    root.cpuHistory = root.record(root.cpuHistory, root.stats.cpu);
                    root.memoryHistory = root.record(root.memoryHistory, root.stats.memory.percent);
                    root.diskHistory = root.record(root.diskHistory, root.stats.disk.percent);
                    // Network graph is relative to the largest sample in this session.
                    root.netHistory = root.record(root.netHistory, root.stats.rx + root.stats.tx);
                } catch (error) {
                    root.status = "Could not read system statistics";
                }
            }
        }
        stderr: StdioCollector {}
        onExited: exitCode => {
            if (root.visible && exitCode !== 0)
                root.status = "Sampler stopped · close and reopen to retry";
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Label {
                    text: "󰍛  System Monitor"
                    Layout.fillWidth: true
                    color: Theme.purple
                    font.pixelSize: 20
                }
                Label {
                    text: root.status
                    color: Theme.muted
                    font.pixelSize: 11
                }
            }
            Label {
                text: root.stats ? "up " + Math.floor(root.stats.uptime / 3600) + "h " + Math.floor(root.stats.uptime % 3600 / 60) + "m" : ""
                color: Theme.muted
                font.pixelSize: 12
            }
            BarButton {
                text: "×"
                hint: "Close · Escape"
                onClicked: root.visible = false
            }
        }
        GridLayout {
            columns: 2
            rowSpacing: 12
            columnSpacing: 12
            Layout.fillWidth: true
            ResourceCard {
                Layout.fillWidth: true
                heading: "CPU"
                value: root.stats ? root.stats.cpu.toFixed(0) + "%" : "—"
                percentage: root.stats ? root.stats.cpu : 0
                history: root.cpuHistory
                detail: root.stats ? root.stats.cores + " threads · load " + root.stats.load.toFixed(2) + (root.stats.temperature !== null ? " · " + root.stats.temperature.toFixed(0) + "°C" : "") : "Waiting for sample"
            }
            ResourceCard {
                Layout.fillWidth: true
                heading: "MEMORY"
                accent: Theme.cyan
                value: root.stats ? root.stats.memory.percent.toFixed(0) + "%" : "—"
                percentage: root.stats ? root.stats.memory.percent : 0
                history: root.memoryHistory
                detail: root.stats ? root.bytes(root.stats.memory.used) + " / " + root.bytes(root.stats.memory.total) : ""
            }
            ResourceCard {
                Layout.fillWidth: true
                heading: "ROOT DISK"
                accent: Theme.yellow
                value: root.stats ? root.stats.disk.percent.toFixed(0) + "%" : "—"
                percentage: root.stats ? root.stats.disk.percent : 0
                history: root.diskHistory
                detail: root.stats ? root.bytes(root.stats.disk.total - root.stats.disk.used) + " free · " + root.bytes(root.stats.disk.total) + " total" : ""
            }
            ResourceCard {
                Layout.fillWidth: true
                heading: "NETWORK"
                accent: Theme.green
                value: root.stats ? "↓ " + root.bytes(root.stats.rx) + "/s" : "—"
                percentage: 0
                history: {
                    const maximum = Math.max(1024, ...root.netHistory);
                    return root.netHistory.map(v => v / maximum * 100);
                }
                detail: root.stats ? "↑ " + root.bytes(root.stats.tx) + "/s · " + (root.stats.interfaces.join(", ") || "offline") : ""
            }
        }
        RowLayout {
            Label {
                text: "ACTIVE PROCESSES"
                color: Theme.muted
                font.pixelSize: 11
                Layout.fillWidth: true
            }
            Label {
                text: "CPU  /  MEMORY"
                color: Theme.muted
                font.pixelSize: 11
            }
        }
        ColumnLayout {
            spacing: 3
            Layout.fillWidth: true
            Repeater {
                model: root.stats ? root.stats.processes : []
                Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: 26
                    radius: 5
                    color: index % 2 === 0 ? Theme.inset : "transparent"
                    required property int index
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        Label {
                            text: String(modelData.pid)
                            Layout.preferredWidth: 64
                            color: Theme.muted
                            font.pixelSize: 11
                        }
                        Label {
                            text: modelData.name
                            Layout.fillWidth: true
                            font.pixelSize: 12
                        }
                        Label {
                            text: modelData.cpu.toFixed(1) + "%"
                            Layout.preferredWidth: 70
                            horizontalAlignment: Text.AlignRight
                            color: Theme.purple
                            font.pixelSize: 12
                        }
                        Label {
                            text: root.bytes(modelData.memory)
                            Layout.preferredWidth: 96
                            horizontalAlignment: Text.AlignRight
                            color: Theme.cyan
                            font.pixelSize: 12
                        }
                    }
                }
            }
        }
        Item {
            Layout.fillHeight: true
        }
        Label {
            Layout.fillWidth: true
            text: root.stats ? "Swap " + root.bytes(root.stats.memory.swapUsed) + " / " + root.bytes(root.stats.memory.swapTotal) + "   ·   Process CPU: 100% = one core   ·   esc close" : "esc close"
            color: Theme.muted
            font.pixelSize: 10
        }
    }
}
