//@ pragma UseQApplication
//@ pragma IconTheme Adwaita
//@ pragma ShellId spectre-dotfiles
//@ pragma Env XCURSOR_THEME = Bibata-Modern-Ice
//@ pragma Env XCURSOR_PATH = /usr/share/icons:/usr/local/share/icons
// SPDX-License-Identifier: GPL-3.0-or-later
// i3/X11 desktop bar. Run with: nixGL quickshell
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.I3
import Quickshell.Io
import Quickshell.X11
import Quickshell.Services.Pipewire
import Quickshell.Services.SystemTray
import Quickshell.Services.UPower
import Quickshell.Widgets

ShellRoot {
    id: root
    property string windowTitle: "Desktop"
    readonly property var sink: Pipewire.defaultAudioSink
    readonly property var audio: sink && sink.ready ? sink.audio : null
    readonly property var battery: UPower.displayDevice
    readonly property bool batteryPresent: battery.isPresent && battery.ready
    readonly property int charge: Math.round(battery.percentage * 100)

    ResourceMonitor { id: systemMonitor }
    IpcHandler {
        target: "desktop"
        function launcher(): void {
            systemMonitor.visible = false;
            Quickshell.execDetached(["rofi", "-show", "drun"]);
        }
        function monitor(): void {
            if (systemMonitor.visible) systemMonitor.visible = false;
            else systemMonitor.open();
        }
        function close(): void { systemMonitor.visible = false; }
    }

    // Own the XEmbed bridge with the shell, so it also stops when the shell exits.
    Process {
        command: ["bash", Quickshell.shellPath("tray-bridge.sh")]
        running: true
        onExited: exitCode => {
            if (exitCode !== 0)
                console.warn("Legacy tray bridge stopped. Stop Polybar before starting Quickshell; see docs/setup.md.");
        }
    }

    PwObjectTracker {
        objects: root.sink ? [root.sink] : []
    }
    SystemClock {
        id: clock
        precision: SystemClock.Minutes
    }

    // Subscribe to title/focus changes; query once per burst, never poll the tree.
    I3IpcListener {
        subscriptions: ["window", "workspace"]
        onIpcEvent: titleDebounce.restart()
    }
    Timer {
        id: titleDebounce
        interval: 50
        onTriggered: {
            if (titleProcess.running)
                restart();
            else
                titleProcess.running = true;
        }
    }
    Process {
        id: titleProcess
        command: ["i3-msg", "-t", "get_tree"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                function focused(node) {
                    if (node.focused && node.window)
                        return node.name || "Untitled";
                    for (const child of (node.nodes || []).concat(node.floating_nodes || [])) {
                        const title = focused(child);
                        if (title !== null)
                            return title;
                    }
                    return null;
                }
                try {
                    root.windowTitle = focused(JSON.parse(text)) || "Desktop";
                } catch (error) {
                    root.windowTitle = "Desktop";
                }
            }
        }
    }

    Variants {
        model: Quickshell.screens
        XPanelWindow {
            id: panel
            required property var modelData
            screen: modelData
            anchors {
                top: true
                left: true
                right: true
            }
            implicitHeight: Theme.barHeight + Theme.topMargin * 2
            // Keep the actual bar alive for tray ownership and the edge sensor.
            // Ignore the temporary spacer below so this surface stays at y=0.
            exclusionMode: ExclusionMode.Ignore
            color: "transparent"
            focusable: false
            // i3 reserves the height of managed dock windows even with zero
            // struts. Use Qt's X11 override-redirect flag on this native backend
            // so hiding the reveal surface itself leaves no permanent gap.
            onWindowConnected: _backingWindow.flags |= Qt.X11BypassWindowManagerHint
            mask: Region {
                width: panel.width
                height: Theme.barRevealHeight
                Region {
                    // Include the margin above the bar so crossing that gap
                    // never ends the hover. All other transparent pixels pass
                    // through to application windows underneath.
                    x: surface.x
                    width: surface.width
                    height: Math.max(0, surface.y + surface.height)
                }
            }

            readonly property bool compact: surface.width < 1100
            readonly property var workspaces: I3.workspaces.values
            property bool showDate: false
            property bool revealed: false
            property real revealProgress: revealed ? 1 : 0
            Behavior on revealProgress {
                NumberAnimation {
                    duration: Theme.barSlideDuration
                    easing.type: Easing.InOutCubic
                }
            }

            PanelWindow {
                // The same eased progress drives the bar and reserved height,
                // so tiled windows move with it instead of jumping by 50px.
                // Unmap at zero: i3 reserves even zero-strut managed docks.
                screen: panel.screen
                visible: panel.revealProgress > 0
                anchors { top: true; left: true; right: true }
                implicitHeight: Math.max(1, Math.round((Theme.barHeight + Theme.topMargin * 2) * panel.revealProgress))
                exclusionMode: ExclusionMode.Auto
                aboveWindows: false
                focusable: false
                color: "transparent"
                mask: Region {}
            }

            HoverHandler {
                id: barHover
                // HoverHandler observes buttons without intercepting clicks,
                // scrolling, or the legacy tray bridge's native interactions.
                onHoveredChanged: {
                    if (hovered) {
                        hideDelay.stop();
                        panel.revealed = true;
                    } else if (panel.revealed) {
                        hideDelay.restart();
                    }
                }
            }

            Timer {
                id: hideDelay
                interval: Math.max(5000, Theme.barHideDelay)
                onTriggered: {
                    if (!barHover.hovered)
                        panel.revealed = false;
                }
            }

            Brightness {
                id: brightness
                external: !/^(eDP|LVDS|DSI)/i.test(panel.screen.name)
            }

            Rectangle {
                id: surface
                anchors.horizontalCenter: parent.horizontalCenter
                y: -height + (height + Theme.topMargin) * panel.revealProgress
                width: Math.min(panel.screen.width - 24, Math.max(Theme.minimumWidth, Math.round(panel.screen.width * Theme.widthFraction)))
                height: Theme.barHeight
                color: Theme.background
                radius: Theme.radius
                border.width: Theme.borderWidth
                border.color: Theme.purple

                RowLayout {
                    id: left
                    anchors.left: parent.left
                    anchors.leftMargin: 7
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4

                    BarButton {
                        text: "󰀻"
                        foreground: Theme.purple
                        hint: "Applications · Super+A"
                        onClicked: { systemMonitor.visible = false; Quickshell.execDetached(["rofi", "-show", "drun"]); }
                    }
                    Divider {
                        Layout.alignment: Qt.AlignVCenter
                    }
                    RowLayout {
                        spacing: 2
                        Repeater {
                            model: 10
                            BarButton {
                                required property int index
                                readonly property int number: index + 1
                                readonly property var workspace: panel.workspaces.find(w => w.number === number) || null
                                text: String(number)
                                implicitWidth: 26
                                horizontalPadding: 3
                                visible: surface.width >= 900 || workspace !== null
                                active: workspace !== null && workspace.active && workspace.monitor !== null && workspace.monitor.name === panel.screen.name
                                foreground: workspace && workspace.urgent ? Theme.red : workspace ? Theme.foreground : Theme.muted
                                hint: "Workspace " + number + (workspace && workspace.monitor ? " · " + workspace.monitor.name : "")
                                onClicked: I3.dispatch("workspace number " + number)
                                onScrolled: direction => I3.dispatch(direction > 0 ? "workspace prev_on_output" : "workspace next_on_output")
                            }
                        }
                        // Preserve named workspaces as well as the ten numbered bindings.
                        Repeater {
                            model: panel.workspaces.filter(w => w.number < 1 || w.number > 10)
                            BarButton {
                                required property var modelData
                                text: modelData.name
                                implicitWidth: Math.min(90, text.length * Theme.fontSize + 16)
                                active: modelData.active && modelData.monitor !== null && modelData.monitor.name === panel.screen.name
                                foreground: modelData.urgent ? Theme.red : Theme.foreground
                                hint: "Workspace " + modelData.name
                                onClicked: I3.dispatch("workspace " + JSON.stringify(modelData.name))
                            }
                        }
                    }
                    Divider {
                        Layout.alignment: Qt.AlignVCenter
                        visible: title.visible
                    }
                    Label {
                        id: title
                        visible: !panel.compact
                        // Leave the clock centered even with a long application title.
                        Layout.preferredWidth: Math.max(0, Math.min(170, surface.width / 2 - 400))
                        text: root.windowTitle
                        color: Theme.muted
                    }
                }

                BarButton {
                    id: clockButton
                    anchors.centerIn: parent
                    text: Qt.formatDateTime(clock.date, panel.showDate ? "ddd, dd MMM" : "hh:mm AP")
                    foreground: Theme.purple
                    hint: Qt.formatDateTime(clock.date, "dddd, d MMMM yyyy") + "\nClick to switch date / time"
                    onClicked: panel.showDate = !panel.showDate
                }

                RowLayout {
                    id: right
                    anchors.right: parent.right
                    anchors.rightMargin: 7
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3

                    BarButton {
                        text: "󰍛"
                        foreground: Theme.purple
                        hint: "System monitor · Super+F12"
                        onClicked: systemMonitor.visible = !systemMonitor.visible
                    }

                    BarButton {
                        text: !root.audio ? "󰖁 —" : root.audio.muted ? "󰖁 muted" : "󰕾 " + Math.round(root.audio.volume * 100) + "%"
                        foreground: !root.audio || root.audio.muted ? Theme.muted : Theme.cyan
                        hint: (root.sink ? root.sink.description + "\n" : "Audio unavailable\n") + "Click: mute · Scroll: volume · Right click: mixer"

                        onClicked: mouse => {
                            if (mouse.button === Qt.RightButton)
                                Quickshell.execDetached(["pavucontrol"]);
                            else if (root.audio)
                                root.audio.muted = !root.audio.muted;
                        }
                        onScrolled: direction => {
                            if (root.audio)
                                root.audio.volume = Math.max(0, Math.min(1, root.audio.volume + direction * 0.05));
                        }
                    }
                    BarButton {
                        visible: root.batteryPresent
                        interactive: false
                        text: (root.battery.state === UPowerDeviceState.Charging ? "󰂄 " : "󰁹 ") + root.charge + "%"
                        foreground: !UPower.onBattery ? Theme.green : root.charge <= 15 ? Theme.red : root.charge <= 30 ? Theme.yellow : Theme.foreground
                        hint: UPowerDeviceState.toString(root.battery.state) + " · " + root.charge + "%"
                    }
                    BarButton {
                        text: "󰃠 " + (brightness.percentage < 0 ? "—" : brightness.percentage + "%")
                        foreground: brightness.percentage < 0 ? Theme.muted : Theme.foreground
                        hint: (brightness.external ? "Monitor brightness (DDC/CI)" : "Backlight brightness") + "\nScroll to adjust · Click to refresh"
                        onClicked: brightness.refresh()
                        onScrolled: direction => brightness.adjust(direction)
                    }
                    Divider {
                        Layout.alignment: Qt.AlignVCenter
                        visible: tray.width > 0
                    }
                    RowLayout {
                        id: tray
                        spacing: 2
                        Repeater {
                            model: SystemTray.items
                            BarButton {
                                id: trayButton
                                required property var modelData
                                implicitWidth: 28
                                hint: modelData.tooltipTitle || modelData.title || modelData.id
                                IconImage {
                                    anchors.centerIn: parent
                                    implicitSize: Theme.iconSize
                                    source: trayButton.modelData.icon
                                }
                                onClicked: mouse => {
                                    if (!modelData.hasMenu) {
                                        // XEmbed proxies open the original GTK/X11 menu via
                                        // ContextMenu, which Quickshell's display() doesn't call.
                                        // GTK/XTest requires the embedded window to be under
                                        // the actual pointer, not below the tray button.
                                        const point = mapToItem(panel.contentItem, mouse.x, mouse.y);
                                        const action = mouse.button === Qt.RightButton ? "ContextMenu"
                                            : mouse.button === Qt.MiddleButton ? "SecondaryActivate" : "Activate";
                                        Quickshell.execDetached(["python3", Quickshell.shellPath("tray-action.py"),
                                            modelData.id, action, String(Math.round(panel.screen.x + point.x)),
                                            String(Math.round(panel.screen.y + point.y))]);
                                    } else if (mouse.button === Qt.MiddleButton)
                                        modelData.secondaryActivate();
                                    else if (mouse.button === Qt.RightButton || modelData.onlyMenu) {
                                        if (modelData.hasMenu) {
                                            const point = mapToItem(panel.contentItem, 0, height);
                                            modelData.display(panel, point.x, point.y);
                                        }
                                    } else
                                        modelData.activate();
                                }
                                onScrolled: direction => modelData.scroll(direction * 120, false)
                            }
                        }
                    }
                    Divider {
                        Layout.alignment: Qt.AlignVCenter
                    }
                    BarButton {
                        text: "⏻"
                        foreground: Theme.purple
                        hint: "Power menu · Super+Backspace"
                        onClicked: Quickshell.execDetached(["bash", Quickshell.shellPath("../rofi/greenpower.sh")])
                    }
                }
            }
        }
    }
}
