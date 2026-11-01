// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Effects
import Quickshell.Widgets

Item {
    implicitWidth: Theme.iconSize
    implicitHeight: Theme.iconSize
    property alias source: icon.source
    property string itemId: ""
    readonly property bool lighten: Theme.lightTrayIcons &&
        ((Theme.lightTrayItemIds || []).indexOf(itemId.toLowerCase()) !== -1 || String(source).includes("-symbolic"))
    // Custom application icons retain their colors. Only known status icons
    // and explicitly symbolic icons receive the light treatment.
    IconImage {
        id: icon
        anchors.fill: parent
        implicitSize: Theme.iconSize
        visible: !parent.lighten
    }
    MultiEffect {
        anchors.fill: parent
        source: icon
        visible: parent.lighten
        brightness: 0.60
        saturation: -1.0
        autoPaddingEnabled: false
    }
}
