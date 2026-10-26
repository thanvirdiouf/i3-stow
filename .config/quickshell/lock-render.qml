//@ pragma ShellId spectre-lock-render
// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import Quickshell

ShellRoot {
    id: root
    readonly property var layout: JSON.parse(Quickshell.env("QS_LOCK_LAYOUT") || '{"width":1280,"height":720,"screens":[{"x":0,"y":0,"width":1280,"height":720}]}')
    FloatingWindow {
        implicitWidth: root.layout.width
        implicitHeight: root.layout.height
        visible: true
        color: Theme.base
        Rectangle {
            id: canvas
            anchors.fill: parent
            color: Theme.base
            Repeater {
                model: root.layout.screens
                LockScreen {
                    required property var modelData
                    x: modelData.x
                    y: modelData.y
                    width: modelData.width
                    height: modelData.height
                    username: Quickshell.env("USER") || "user"
                }
            }
        }
        Timer {
            interval: 150
            running: true
            onTriggered: canvas.grabToImage(result => {
                if (!result.saveToFile(Quickshell.env("QS_LOCK_OUTPUT")))
                    console.error("Could not save lockscreen artwork");
                Qt.quit();
            }, Qt.size(root.layout.width, root.layout.height))
        }
    }
}
