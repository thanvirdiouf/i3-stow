// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io

FloatingWindow {
    id: root
    title: "Spectre · Workspaces"
    visible: false
    color: "transparent"
    required property var backend
    property var choices: []
    property int selected: 0
    readonly property int columns: Math.max(1, Math.min(3, choices.length))
    implicitWidth: Math.min(screen ? screen.width - 48 : 940, Math.max(420, columns * 286 + 48))
    implicitHeight: Math.min(screen ? screen.height - 48 : 680, 158 + Math.ceil(choices.length / columns) * 214)

    function cycle(direction): void {
        if (visible) {
            selected = (selected + direction + choices.length) % choices.length;
            grid.positionViewAtIndex(selected, GridView.Contain);
            return;
        }
        if (!backend) return;
        const available = backend.workspaces.filter(w => w.focused || w.occupied !== false);
        if (available.length === 0) return;
        // Freeze the list for this gesture: mapping this window changes focus,
        // and background applications may open or close while Super is held.
        const current = available.find(w => w.focused) || available.find(w => w.active) || available[0];
        choices = available.map(w => ({
            name: w.name, number: w.number, monitor: w.monitor ? w.monitor.name : "",
            current: w.name === current.name, windows: w.windows || [],
            recency: w.recency === undefined ? -1 : w.recency, urgent: w.urgent
        })).sort((a, b) => Number(b.current) - Number(a.current) || b.recency - a.recency
            || (a.number >= 0 && b.number >= 0 ? a.number - b.number : a.name.localeCompare(b.name)));
        screen = Quickshell.screens.find(s => s.name === (current.monitor ? current.monitor.name : "")) || Quickshell.screens[0];
        selected = (direction + choices.length) % choices.length;
        visible = true;
        content.forceActiveFocus();
        grid.positionViewAtIndex(selected, GridView.Contain);
    }
    function accept(): void {
        if (!visible) return;
        const name = choices[selected].name;
        visible = false;
        backend.focusWorkspace(name);
    }
    function cancel(): void { visible = false; }
    onClosed: cancel()

    Process {
        command: ["python3", Quickshell.shellPath("super-release.py")]
        running: root.visible
        stdout: SplitParser { onRead: data => { if (data === "released") root.accept(); } }
        onExited: exitCode => { if (exitCode !== 0 && root.visible) root.cancel(); }
    }

    Rectangle {
        id: content
        anchors.fill: parent
        color: Theme.background
        radius: Theme.panelRadius
        border.width: Theme.borderWidth
        border.color: Theme.purple
        focus: true
        Keys.onPressed: event => {
            if (event.key === Qt.Key_Escape) root.cancel();
            else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) root.accept();
            else if (event.key === Qt.Key_Backtab || event.key === Qt.Key_Left) root.cycle(-1);
            else if (event.key === Qt.Key_Tab) root.cycle(event.modifiers & Qt.ShiftModifier ? -1 : 1);
            else if (event.key === Qt.Key_Right) root.cycle(1);
            else { event.accepted = true; return; }
            event.accepted = true;
        }
        opacity: root.visible ? 1 : 0
        scale: root.visible ? 1 : .97
        Behavior on opacity { NumberAnimation { duration: 100 } }
        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

        RowLayout {
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 26 }
            ColumnLayout {
                spacing: 5
                Text {
                    text: "WORKSPACES"
                    color: Theme.cyan
                    font { family: Theme.font; pixelSize: 12; letterSpacing: 2 }
                }
                Text {
                    text: "Choose where to continue"
                    color: Theme.foreground
                    font { family: Theme.font; pixelSize: 19; bold: true }
                }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: (root.selected + 1) + " / " + root.choices.length
                color: Theme.muted
                font { family: Theme.font; pixelSize: 14 }
            }
        }

        GridView {
            id: grid
            anchors { left: parent.left; right: parent.right; top: parent.top; bottom: footer.top; leftMargin: 22; rightMargin: 22; topMargin: 94; bottomMargin: 14 }
            clip: true
            cellWidth: width / root.columns
            cellHeight: 214
            model: root.choices
            currentIndex: root.selected
            boundsBehavior: Flickable.StopAtBounds
            delegate: Item {
                required property var modelData
                required property int index
                width: grid.cellWidth
                height: grid.cellHeight
                Rectangle {
                    id: card
                    anchors { fill: parent; margins: 6 }
                    readonly property bool chosen: index === root.selected
                    color: chosen ? Theme.surface : Theme.inset
                    radius: 13
                    border { width: chosen ? 2 : 1; color: chosen ? Theme.purple : Theme.border }
                    Behavior on color { ColorAnimation { duration: 90 } }
                    RowLayout {
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 13 }
                        spacing: 9
                        Rectangle {
                            width: 34; height: 30; radius: 7
                            color: card.chosen ? Theme.purple : Theme.base
                            Text {
                                anchors.centerIn: parent
                                text: modelData.name
                                color: card.chosen ? Theme.base : Theme.foreground
                                font { family: Theme.font; pixelSize: 16; bold: true }
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.monitor
                            elide: Text.ElideRight
                            color: Theme.muted
                            font { family: Theme.font; pixelSize: 11 }
                        }
                        Text {
                            text: modelData.current ? "CURRENT" : modelData.urgent ? "•" : ""
                            color: modelData.urgent ? Theme.red : Theme.cyan
                            font { family: Theme.font; pixelSize: 9 }
                        }
                    }
                    Rectangle {
                        id: preview
                        anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: 14; rightMargin: 14; topMargin: 56 }
                        height: 94
                        radius: 6
                        color: Theme.base
                        clip: true
                        Repeater {
                            model: modelData.windows
                            Rectangle {
                                required property var modelData
                                x: Math.max(0, modelData.x) * preview.width + 2
                                y: Math.max(0, modelData.y) * preview.height + 2
                                width: Math.max(12, Math.min(1 - Math.max(0, modelData.x), modelData.width) * preview.width - 4)
                                height: Math.max(10, Math.min(1 - Math.max(0, modelData.y), modelData.height) * preview.height - 4)
                                radius: 4
                                color: card.chosen ? "#474052" : Theme.inset
                                border { width: 1; color: card.chosen ? Theme.purple : Theme.border }
                                Text {
                                    anchors { fill: parent; margins: 5 }
                                    text: modelData.app
                                    elide: Text.ElideRight
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: Text.AlignHCenter
                                    color: Theme.muted
                                    font { family: Theme.font; pixelSize: 9 }
                                }
                            }
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: modelData.windows.length === 0
                            text: "No windows"
                            color: Theme.muted
                            font { family: Theme.font; pixelSize: 11 }
                        }
                    }
                    Text {
                        anchors { left: parent.left; right: parent.right; top: preview.bottom; margins: 13 }
                        text: modelData.windows.length ? modelData.windows.map(w => w.app).filter((v, i, a) => a.indexOf(v) === i).join(" · ") : "Empty workspace"
                        elide: Text.ElideRight
                        color: card.chosen ? Theme.foreground : Theme.muted
                        font { family: Theme.font; pixelSize: 12 }
                    }
                    MouseArea {
                        anchors.fill: parent
                        // Mapping the popup under a stationary pointer must
                        // not replace the keyboard's selection.
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { root.selected = index; root.accept(); }
                    }
                }
            }
        }
        RowLayout {
            id: footer
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 26 }
            Text {
                visible: root.width >= 600
                text: "Super + Tab  next     Shift  reverse"
                color: Theme.muted
                font { family: Theme.font; pixelSize: 11 }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "Release Super to switch · Esc to cancel"
                color: Theme.muted
                font { family: Theme.font; pixelSize: 11 }
            }
        }
    }
}
