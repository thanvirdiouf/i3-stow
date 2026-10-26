// SPDX-License-Identifier: GPL-3.0-or-later
pragma Singleton
import QtQuick

QtObject {
    // Dracula, shared with i3 and Rofi. Keep the bar compact like Polybar.
    readonly property color background: "#f2282a36"
    readonly property color surface: "#44475a"
    readonly property color base: "#282a36"
    readonly property color inset: "#21222c"
    readonly property int panelRadius: 20
    readonly property color foreground: "#f8f8f2"
    readonly property color muted: "#8990ad"
    readonly property color purple: "#bd93f9"
    readonly property color border: "#694b8a"
    readonly property color cyan: "#8be9fd"
    readonly property color green: "#50fa7b"
    readonly property color yellow: "#f1fa8c"
    readonly property color red: "#ff5555"
    readonly property string font: "JetBrainsMono Nerd Font"
    readonly property int fontSize: 14
    readonly property int iconSize: 18
    readonly property int barHeight: 38
    readonly property int topMargin: 6
    readonly property int barRevealHeight: 4
    readonly property int barHideDelay: 5000
    readonly property int barSlideDuration: 320
    readonly property real widthFraction: 0.60
    readonly property int minimumWidth: 1040
    readonly property int radius: 10
    readonly property int borderWidth: 2
}
