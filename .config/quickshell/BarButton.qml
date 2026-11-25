// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "." as Components

Rectangle {
    id: root
    property string text: ""
    property string hint: ""
    property int hintTimeout: 6000
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
        id: tip
        readonly property int shadowMargin: 10
        // A dock is shallow. A native popup can extend below it without
        // covering the button and intercepting subsequent wheel events.
        popupType: Popup.Window
        y: root.height
        padding: shadowMargin + 6
        visible: mouse.containsMouse && root.hint.length > 0
        delay: 600
        timeout: root.hintTimeout
        text: root.hint
        contentItem: Components.Label {
            text: root.hint
            elide: Text.ElideNone
        }
        background: Item {
            RectangularShadow {
                anchors.fill: bubble
                radius: bubble.radius
                blur: 8
                offset: Qt.vector2d(0, 2)
                color: "#66000000"
            }
            Rectangle {
                id: bubble
                anchors.fill: parent
                anchors.margins: tip.shadowMargin
                color: Theme.base
                radius: 7
                border.color: Theme.border
            }
        }
    }
}
