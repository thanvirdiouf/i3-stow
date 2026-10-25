// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import "." as Components

Rectangle {
    id: root
    property string text: ""
    property string hint: ""
    property color foreground: Theme.foreground
    property bool active: false
    property bool interactive: true
    property int horizontalPadding: 8
    readonly property bool hovered: mouse.containsMouse
    signal clicked(var mouse)
    signal scrolled(int direction)

    implicitWidth: label.implicitWidth + horizontalPadding * 2
    implicitHeight: 28
    radius: 7
    color: active ? Theme.purple : hovered && interactive ? Theme.surface : "transparent"
    Behavior on color {
        ColorAnimation {
            duration: 120
        }
    }

    Components.Label {
        id: label
        anchors.centerIn: parent
        width: Math.min(implicitWidth, Math.max(0, root.width - root.horizontalPadding * 2))
        text: root.text
        color: root.active ? "#282a36" : root.foreground
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: root.interactive ? Qt.LeftButton | Qt.RightButton | Qt.MiddleButton : Qt.NoButton
        cursorShape: root.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: event => root.clicked(event)
        onWheel: event => {
            const delta = event.angleDelta.y || event.angleDelta.x;
            if (root.interactive && delta !== 0)
                root.scrolled(delta > 0 ? 1 : -1);
            event.accepted = root.interactive;
        }
    }

    ToolTip {
        // A dock is shallow. A native popup can extend below it without
        // covering the button and intercepting subsequent wheel events.
        popupType: Popup.Window
        y: root.height + 8
        visible: mouse.containsMouse && root.hint.length > 0
        delay: 600
        timeout: 6000
        text: root.hint
        contentItem: Components.Label {
            text: root.hint
            elide: Text.ElideNone
        }
        background: Rectangle {
            color: Theme.background
            radius: 7
            border.color: Theme.border
        }
    }
}
