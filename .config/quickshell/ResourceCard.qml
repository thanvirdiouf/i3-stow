// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string heading
    property string value
    property string detail
    property real percentage: 0
    property color accent: Theme.purple
    property var history: []
    implicitHeight: 148
    radius: 12
    color: Theme.inset
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 8
        RowLayout {
            Label {
                text: root.heading
                color: Theme.muted
                Layout.fillWidth: true
                font.pixelSize: 12
            }
            Label {
                text: root.value
                color: root.accent
                font.pixelSize: 21
            }
        }
        Canvas {
            id: graph
            Layout.fillWidth: true
            Layout.fillHeight: true
            onPaint: {
                const ctx = getContext("2d");
                ctx.reset();
                ctx.strokeStyle = Theme.border;
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(0, height - 1);
                ctx.lineTo(width, height - 1);
                ctx.stroke();
                const points = root.history;
                if (points.length < 2)
                    return;
                ctx.beginPath();
                for (let i = 0; i < points.length; ++i) {
                    const x = width * i / (points.length - 1);
                    const y = height - 2 - Math.max(0, Math.min(100, points[i])) / 100 * (height - 4);
                    if (i === 0)
                        ctx.moveTo(x, y);
                    else
                        ctx.lineTo(x, y);
                }
                ctx.strokeStyle = root.accent;
                ctx.lineWidth = 2;
                ctx.stroke();
                ctx.lineTo(width, height);
                ctx.lineTo(0, height);
                ctx.closePath();
                ctx.globalAlpha = 0.12;
                ctx.fillStyle = root.accent;
                ctx.fill();
            }
            Connections {
                target: root
                function onHistoryChanged() {
                    graph.requestPaint();
                }
            }
            onWidthChanged: requestPaint()
        }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 3
            color: Theme.surface
            radius: 2
            Rectangle {
                height: parent.height
                width: parent.width * Math.max(0, Math.min(100, root.percentage)) / 100
                color: root.accent
                radius: 2
            }
        }
        Label {
            text: root.detail
            color: Theme.muted
            font.pixelSize: 11
            Layout.fillWidth: true
        }
    }
}
