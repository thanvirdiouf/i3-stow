// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick

// Artwork only. i3lock owns the keyboard, password indicator, and authentication.
// Leave the center of each monitor clear for its native 180px indicator.
Rectangle {
    id: root
    property date timestamp: new Date()
    property string username: "spectre"
    color: Theme.base

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.72, 880)
        height: width
        radius: width / 2
        color: "transparent"
        border.width: 1
        border.color: "#353140"
        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.78
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: "#353140"
        }
    }
    Rectangle {
        x: 28
        y: 28
        width: parent.width - 56
        height: parent.height - 56
        radius: Theme.panelRadius
        color: "transparent"
        border.width: 2
        border.color: Theme.border
    }
    Row {
        x: 56
        y: 52
        spacing: 12
        Label {
            text: ""
            color: Theme.purple
            font.pixelSize: 18
        }
        Label {
            text: "SESSION LOCKED"
            color: Theme.muted
            font.pixelSize: 12
            font.letterSpacing: 2
        }
    }
    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height / 2 - 240
        spacing: 8
        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Qt.formatDateTime(root.timestamp, "hh:mm")
            color: Theme.purple
            font.pixelSize: 76
            font.weight: Font.Light
        }
        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Qt.formatDateTime(root.timestamp, "dddd, d MMMM")
            color: Theme.foreground
            font.pixelSize: 16
        }
    }
    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height / 2 + 125
        spacing: 14
        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.username
            font.pixelSize: 18
            color: Theme.purple
        }
        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Type your password and press Enter"
            font.pixelSize: 12
            color: Theme.muted
        }
    }
    Rectangle {
        anchors.centerIn: parent
        width: 178
        height: width
        radius: width / 2
        color: Theme.inset
        border.width: 2
        border.color: Theme.border
        Label {
            anchors.centerIn: parent
            text: ""
            color: Theme.purple
            font.pixelSize: 38
        }
    }
    Label {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 54
        text: "  A moment away."
        color: Theme.muted
        font.pixelSize: 11
        font.letterSpacing: 1
    }
}
