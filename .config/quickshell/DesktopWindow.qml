// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import Quickshell

FloatingWindow {
    id: root
    visible: false
    color: "transparent"
    signal dismissed
    default property alias body: content.data

    Rectangle {
        anchors.fill: parent
        color: Theme.base
        radius: Theme.panelRadius
        border.width: Theme.borderWidth
        border.color: Theme.purple
        Item {
            id: content
            anchors.fill: parent
            anchors.margins: 24
            focus: true
            Keys.onEscapePressed: root.visible = false
        }
    }
    onClosed: visible = false
    onVisibleChanged: {
        if (visible)
            content.forceActiveFocus();
        else
            dismissed();
    }
}
