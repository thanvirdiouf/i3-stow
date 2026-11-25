//@ pragma UseQApplication
//@ pragma IconTheme Adwaita
//@ pragma ShellId spectre-dotfiles
//@ pragma Env XCURSOR_THEME = Bibata-Modern-Ice
//@ pragma Env XCURSOR_PATH = /usr/share/icons:/usr/local/share/icons
// SPDX-License-Identifier: GPL-3.0-or-later
// i3/bspwm X11 desktop bar. Run with: nixGL quickshell
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.X11
import Quickshell.Services.Pipewire
import Quickshell.Services.SystemTray
import Quickshell.Services.UPower
import Quickshell.Widgets

ShellRoot {
    id: root
    readonly property bool bspwm: Quickshell.env("SPECTRE_WM") === "bspwm" || Quickshell.env("XDG_CURRENT_DESKTOP").toLowerCase().includes("bspwm")
    readonly property string windowTitle: desktopBackend.item ? desktopBackend.item.windowTitle : "Desktop"
    readonly property var sink: Pipewire.defaultAudioSink
    readonly property var audio: sink && sink.ready ? sink.audio : null
    readonly property var battery: UPower.displayDevice
    readonly property bool batteryPresent: battery.isPresent && battery.ready
    readonly property int charge: Math.round(battery.percentage * 100)

    ResourceMonitor { id: systemMonitor }
    Process {
        id: usageSampler
        property var sample: null
        function percent(value) {
            return value == null ? "—" : Math.round(value) + "%";
        }
        function coreHint(screenHeight) {
            if (!sample)
                return "Reading CPU counters…";
            const lines = sample.cores.map(core => {
                const temp = core.temperature == null ? "—" : Math.round(core.temperature) + "°C";
                const threads = (core.threads ?? []).map(t => "CPU " + t.id + " " + percent(t.usage).padStart(4));
                return core.label + "  " + percent(core.usage).padStart(4) + "  " + temp.padStart(4)
                    + "    " + threads.join("  ");
            });
            // Lay out long core lists in columns so the tooltip fits below the bar.
            const perColumn = Math.max(1, Math.floor((screenHeight - Theme.barHeight - 96) / (Theme.fontSize * 1.6)));
            const rows = [];
            const width = Math.max(0, ...lines.map(line => line.length)) + 3;
            for (let i = 0; i < Math.min(lines.length, perColumn); ++i) {
                let row = lines[i];
                for (let j = i + perColumn; j < lines.length; j += perColumn)
                    row = row.padEnd(width * Math.floor(j / perColumn)) + lines[j];
                rows.push(row);
            }
            if (sample.cores.some(core => core.temperature == null))
                rows.push(sample.cpuSensor == null ? "—  Core sensor unavailable" : "CPU sensor: " + Math.round(sample.cpuSensor) + "°C");
            return ["Core usage and temperature    Thread usage", ...rows].join("\n");
        }
        command: ["sh", Quickshell.shellPath("resources.sh"), "--summary"]
        running: true
        stdout: SplitParser {
            onRead: line => { usageSampler.sample = JSON.parse(line); }
        }
        onExited: {
            sample = null;
            retryUsage.restart();
        }
    }
    Timer { id: retryUsage; interval: 2000; onTriggered: usageSampler.running = true }
    WorkspaceSwitcher { id: workspaceSwitcher; backend: desktopBackend.item }
    IpcHandler {
        target: "desktop"
        function launcher(): void {
            systemMonitor.visible = false;
            Quickshell.execDetached(["rofi", "-show", "drun"]);
        }
        function monitor(): void {
            workspaceSwitcher.cancel();
            if (systemMonitor.visible) systemMonitor.visible = false;
            else systemMonitor.open();
        }
        function workspaceNext(): void { systemMonitor.visible = false; workspaceSwitcher.cycle(1); }
        function workspacePrevious(): void { systemMonitor.visible = false; workspaceSwitcher.cycle(-1); }
        function close(): void { systemMonitor.visible = false; workspaceSwitcher.cancel(); }
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

    Loader {
        id: desktopBackend
        source: root.bspwm ? "BspwmBackend.qml" : "I3Backend.qml"
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
            implicitHeight: Theme.barHeight
            exclusionMode: root.bspwm ? ExclusionMode.Ignore : ExclusionMode.Auto
            focusable: false
            color: Theme.background

            readonly property bool compact: surface.width < 1100
            readonly property var workspaces: desktopBackend.item ? desktopBackend.item.workspaces : []
            property bool showDate: false

            Brightness {
                id: brightness
                external: !/^(eDP|LVDS|DSI)/i.test(panel.screen.name)
            }

            Item {
                id: surface
                anchors.fill: parent

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
                                foreground: workspace && workspace.urgent ? Theme.red : workspace && workspace.occupied !== false ? Theme.foreground : Theme.muted
                                hint: "Workspace " + number + (workspace && workspace.monitor ? " · " + workspace.monitor.name : "")
                                onClicked: desktopBackend.item.focusWorkspace(String(number))
                                onScrolled: direction => desktopBackend.item.scrollWorkspace(direction)
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
                                onClicked: desktopBackend.item.focusWorkspace(modelData.name)
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
                    anchors.verticalCenter: parent.verticalCenter
                    x: Math.min(Math.max((parent.width - width) / 2, left.x + left.width + 3), right.x - width - 3)
                    visible: x >= left.x + left.width
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
                        text: "CPU " + usageSampler.percent(usageSampler.sample?.cpu)
                            + "  RAM " + usageSampler.percent(usageSampler.sample?.ram)
                        foreground: Theme.purple
                        hint: hovered ? usageSampler.coreHint(panel.screen.height) : ""
                        hintTimeout: -1
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
                                TrayIcon {
                                    anchors.centerIn: parent
                                    itemId: trayButton.modelData.id
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
