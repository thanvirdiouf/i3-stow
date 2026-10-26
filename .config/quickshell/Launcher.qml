// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Widgets
import "." as Components

DesktopWindow {
    id: root
    title: "Spectre · Applications"
    implicitWidth: 660
    implicitHeight: 570
    property string error: ""
    readonly property var results: {
        const terms = search.text.toLowerCase().trim().split(/\s+/).filter(Boolean);
        return DesktopEntries.applications.values.map(entry => {
            const name = entry.name.toLowerCase();
            const haystack = [name, entry.genericName, entry.comment, entry.id, entry.keywords.join(" "), entry.categories.join(" ")].join(" ").toLowerCase();
            return {
                entry: entry,
                score: terms.every(t => haystack.includes(t)) ? terms.reduce((sum, t) => sum + (name.startsWith(t) ? 0 : name.includes(t) ? 1 : 2), 0) : -1
            };
        }).filter(row => row.score >= 0).sort((a, b) => a.score - b.score || a.entry.name.localeCompare(b.entry.name));
    }

    function open() {
        search.text = "";
        error = "";
        visible = true;
        search.forceActiveFocus();
    }
    function launch(index) {
        if (index < 0 || index >= results.length || launchProcess.running)
            return;
        // GIO implements desktop Exec field codes, Terminal, Path, and DBusActivatable.
        // Passing the id as an argument never evaluates an application's Exec in a shell.
        launchProcess.command = ["python3", Quickshell.shellPath("launch-app.py"), results[index].entry.id];
        launchProcess.running = true;
    }

    Process {
        id: launchProcess
        stderr: StdioCollector {
            onStreamFinished: root.error = text.trim()
        }
        onExited: exitCode => {
            if (exitCode === 0)
                root.visible = false;
            else if (!root.error)
                root.error = "Could not start this application.";
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 16
        RowLayout {
            Components.Label {
                text: "󰀻  Applications"
                font.pixelSize: 20
                color: Theme.purple
                Layout.fillWidth: true
            }
            BarButton {
                text: ""
                hint: "Lock screen"
                onClicked: {
                    root.visible = false;
                    Quickshell.execDetached(["sh", Quickshell.shellPath("../i3/lock.sh")]);
                }
            }
            BarButton {
                text: "×"
                hint: "Close · Escape"
                onClicked: root.visible = false
            }
        }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 54
            radius: 12
            color: Theme.inset
            border.color: search.activeFocus ? Theme.purple : Theme.border
            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                Components.Label {
                    text: ""
                    color: Theme.purple
                    font.pixelSize: 20
                }
                TextField {
                    id: search
                    Layout.fillWidth: true
                    padding: 0
                    color: Theme.foreground
                    placeholderText: "Search applications…"
                    placeholderTextColor: Theme.muted
                    font.family: Theme.font
                    font.pixelSize: 16
                    background: Item {}
                    selectByMouse: true
                    onTextChanged: apps.currentIndex = 0
                    Keys.onDownPressed: apps.currentIndex = Math.min(apps.count - 1, apps.currentIndex + 1)
                    Keys.onUpPressed: apps.currentIndex = Math.max(0, apps.currentIndex - 1)
                    Keys.onReturnPressed: root.launch(apps.currentIndex)
                    Keys.onEnterPressed: root.launch(apps.currentIndex)
                    Keys.onEscapePressed: root.visible = false
                }
            }
        }
        ListView {
            id: apps
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 5
            model: root.results
            currentIndex: 0
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }
            onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
            delegate: Rectangle {
                id: row
                required property var modelData
                required property int index
                width: apps.width
                height: 66
                radius: 10
                readonly property bool selected: apps.currentIndex === index
                color: selected ? Theme.purple : mouse.containsMouse ? Theme.surface : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 14
                    Rectangle {
                        implicitWidth: 32
                        implicitHeight: 32
                        radius: 7
                        color: row.selected ? Theme.base : Theme.surface
                        Components.Label {
                            anchors.centerIn: parent
                            text: row.modelData.entry.name.slice(0, 1).toUpperCase()
                            color: Theme.purple
                            visible: appIcon.status !== Image.Ready
                        }
                        IconImage {
                            id: appIcon
                            anchors.centerIn: parent
                            implicitSize: 30
                            source: Quickshell.iconPath(row.modelData.entry.icon, true)
                            visible: status === Image.Ready
                        }
                    }
                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true
                        Components.Label {
                            text: row.modelData.entry.name
                            color: row.selected ? Theme.base : Theme.foreground
                            Layout.fillWidth: true
                        }
                        Components.Label {
                            text: row.modelData.entry.genericName || row.modelData.entry.comment || row.modelData.entry.id
                            font.pixelSize: 11
                            color: row.selected ? Theme.base : Theme.muted
                            Layout.fillWidth: true
                        }
                    }
                    Components.Label {
                        text: "↵"
                        visible: row.selected
                        color: Theme.base
                    }
                }
                MouseArea {
                    id: mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        apps.currentIndex = row.index;
                        root.launch(row.index);
                    }
                }
            }
            Components.Label {
                anchors.centerIn: parent
                visible: apps.count === 0
                text: "No matching applications"
                color: Theme.muted
            }
        }
        Components.Label {
            visible: root.error.length > 0
            text: root.error
            color: Theme.red
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            elide: Text.ElideNone
        }
        RowLayout {
            Components.Label {
                text: apps.count + (apps.count === 1 ? " application" : " applications")
                color: Theme.muted
                font.pixelSize: 11
                Layout.fillWidth: true
            }
            Components.Label {
                text: "↑↓ navigate   ↵ launch   esc close"
                color: Theme.muted
                font.pixelSize: 11
            }
        }
    }
}
