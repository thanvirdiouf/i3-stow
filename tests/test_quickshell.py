# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression coverage for XDG launching and the X11 lock/suspend handoff.

All locker and display commands are fixtures. These tests never lock a session.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / ".config/quickshell"


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SHELL / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher = load_module("launcher", "launch-app.py")
locker = load_module("locker", "lock-screen.py")
resources = load_module("resources", "resources.py")


class DesktopEntries(unittest.TestCase):
    @unittest.skipUnless(shutil.which("gio"), "GIO is not installed")
    def test_real_gio_expands_desktop_fields_without_a_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            applications = base / "applications"
            applications.mkdir()
            capture = base / "capture.json"
            script = base / "capture.py"
            script.write_text("import json, sys\nfrom pathlib import Path\n"
                              f"Path({str(capture)!r}).write_text(json.dumps(sys.argv[1:]))\n")
            entry = applications / "fixture.desktop"
            entry.write_text("[Desktop Entry]\nType=Application\nName=Fixture App\n"
                             "Icon=utilities-terminal\nTerminal=false\n"
                             f"Exec={sys.executable} {script} %c %i\n")
            env = dict(os.environ, XDG_DATA_HOME=str(base), XDG_DATA_DIRS=str(base))
            subprocess.run([sys.executable, str(SHELL / "launch-app.py"), "fixture"],
                           env=env, check=True, capture_output=True, timeout=5)
            for _ in range(40):
                if capture.exists():
                    break
                time.sleep(0.05)
            self.assertEqual(json.loads(capture.read_text()),
                             ["Fixture App", "--icon", "utilities-terminal"])

    def test_user_override_and_nested_desktop_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            user, system = Path(directory) / "user", Path(directory) / "system"
            for root in [user, system]:
                (root / "applications/vendor").mkdir(parents=True)
                (root / "applications/vendor/tool.desktop").write_text("[Desktop Entry]\n")
            with patch.dict(os.environ, XDG_DATA_HOME=str(user), XDG_DATA_DIRS=str(system)):
                self.assertEqual(launcher.desktop_file("vendor-tool"), user / "applications/vendor/tool.desktop")
                self.assertEqual(launcher.desktop_file("vendor-tool.desktop"), user / "applications/vendor/tool.desktop")
                with self.assertRaises(FileNotFoundError):
                    launcher.desktop_file("../../missing")

    def test_failed_gio_launch_is_reported(self):
        with patch.object(launcher, "desktop_file", return_value=Path("/tmp/example.desktop")), \
             patch.object(launcher.shutil, "which", return_value="/usr/bin/gio"), \
             patch.object(launcher.subprocess, "run", return_value=subprocess.CompletedProcess([], 7)) as run, \
             patch.object(sys, "argv", ["launch-app.py", "example"]):
            self.assertEqual(launcher.main(), 7)
            self.assertEqual(run.call_args.args[0], ["gio", "launch", "/tmp/example.desktop"])


class ControlPath(unittest.TestCase):
    def test_stow_symlink_identity_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "dotfiles"
            source.mkdir()
            shutil.copy(SHELL / "control.sh", source)
            linked = base / "quickshell"
            linked.symlink_to(source, target_is_directory=True)
            binary = base / "bin"
            binary.mkdir()
            quickshell = binary / "quickshell"
            capture = base / "args.json"
            quickshell.write_text(f"#!{sys.executable}\nimport json,sys\nfrom pathlib import Path\n"
                                  f"Path({str(capture)!r}).write_text(json.dumps(sys.argv[1:]))\n")
            quickshell.chmod(0o755)
            env = dict(os.environ, PATH=str(binary) + ":" + os.environ["PATH"])
            subprocess.run(["sh", str(linked / "control.sh"), "monitor"], env=env,
                           check=True, capture_output=True, timeout=5)
            self.assertEqual(json.loads(capture.read_text()),
                             ["ipc", "--path", str(linked / "shell.qml"), "call", "desktop", "monitor"])


class LockHandoff(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.env = os.environ.copy()
        self.env.pop("XSS_SLEEP_LOCK_FD", None)
        self.env.update(PATH=str(self.bin) + ":" + self.env["PATH"],
                        XDG_CACHE_HOME=str(self.base / "cache"),
                        LOCK_TEST_CAPTURE=str(self.base / "result.json"))
        self.executable("xrandr", "print('Screen 0: current 1920 x 1080, maximum 32767 x 32767')\nprint('DP-1 connected primary 1920x1080+0+0')")
        self.executable("quickshell", "import os\nfrom pathlib import Path\nPath(os.environ['QS_LOCK_OUTPUT']).write_bytes(b'\\x89PNG\\r\\n\\x1a\\n' + b'x' * 128)")
        self.executable("i3lock", """import json, os, sys
from pathlib import Path
result = {'args': sys.argv[1:]}
if '--image' in sys.argv:
    image = sys.argv[sys.argv.index('--image') + 1]
    result['png'] = Path(image).read_bytes().startswith(b'\\x89PNG\\r\\n\\x1a\\n')
if 'XSS_SLEEP_LOCK_FD' in os.environ:
    result['sleep_fd_open'] = os.fstat(int(os.environ['XSS_SLEEP_LOCK_FD'])).st_mode > 0
Path(os.environ['LOCK_TEST_CAPTURE']).write_text(json.dumps(result))
""")

    def executable(self, name, source):
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\n" + source + "\n")
        path.chmod(0o755)

    def run_locker(self, **kwargs):
        subprocess.run([sys.executable, str(SHELL / "lock-screen.py")], env=self.env,
                       capture_output=True, check=True, timeout=10, **kwargs)
        return json.loads((self.base / "result.json").read_text())

    def test_manual_artwork_survives_exec_and_temporary_cleanup(self):
        result = self.run_locker()
        self.assertTrue(result["png"])
        self.assertIn("--nofork", result["args"])

    def test_active_animated_locker_preserves_sleep_descriptor(self):
        with tempfile.TemporaryFile() as sleep:
            self.env["XSS_SLEEP_LOCK_FD"] = str(sleep.fileno())
            subprocess.run(["sh", str(ROOT / ".config/i3/lock.sh")], env=self.env,
                           pass_fds=(sleep.fileno(),), capture_output=True, check=True, timeout=5)
        result = json.loads((self.base / "result.json").read_text())
        self.assertEqual(result["args"], ["--nofork", "--color=1e1e2e",
                                       "--image=" + str(ROOT / ".config/i3/lockscreen-image.png")])
        self.assertTrue(result["sleep_fd_open"])

    def test_active_locker_without_image_uses_solid_padlock_fallback(self):
        wrapper = self.base / "lock.sh"
        shutil.copy(ROOT / ".config/i3/lock.sh", wrapper)
        subprocess.run(["sh", str(wrapper)], env=self.env,
                       capture_output=True, check=True, timeout=5)
        result = json.loads((self.base / "result.json").read_text())
        self.assertEqual(result["args"], ["--nofork", "--color=1e1e2e"])

    def test_renderer_failure_still_execs_solid_locker(self):
        self.executable("quickshell", "raise SystemExit(1)")
        self.assertEqual(self.run_locker()["args"], ["--nofork", "--color=282a36"])

    def test_suspend_never_renders_and_preserves_sleep_descriptor(self):
        self.executable("quickshell", "raise RuntimeError('must not render during suspend')")
        self.executable("xrandr", "raise RuntimeError('must not query monitors during suspend')")
        cache = self.base / "cache/quickshell/spectre-lock.png"
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b'\x89PNG\r\n\x1a\n' + b'x' * 128)
        with tempfile.TemporaryFile() as sleep:
            self.env["XSS_SLEEP_LOCK_FD"] = str(sleep.fileno())
            result = self.run_locker(pass_fds=(sleep.fileno(),))
        self.assertTrue(result["sleep_fd_open"])
        self.assertTrue(result["png"])

    def test_suspend_without_cache_still_locks(self):
        with tempfile.TemporaryFile() as sleep:
            self.env["XSS_SLEEP_LOCK_FD"] = str(sleep.fileno())
            result = self.run_locker(pass_fds=(sleep.fileno(),))
        self.assertTrue(result["sleep_fd_open"])
        self.assertNotIn("--image", result["args"])

    def test_monitor_layout_preserves_offsets_and_deduplicates_mirrors(self):
        output = """Screen 0: current 4480 x 1440, maximum 32767 x 32767
DP-1 connected primary 2560x1440+1920+0
HDMI-1 connected 1920x1080+0+180
HDMI-2 connected 1920x1080+0+180
eDP-1 disconnected
"""
        with patch.object(locker.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output)):
            layout = locker.screen_layout()
        self.assertEqual((layout["width"], layout["height"]), (4480, 1440))
        self.assertEqual(len(layout["screens"]), 2)
        self.assertEqual(layout["screens"][1]["y"], 180)


class ResourceSnapshots(unittest.TestCase):
    def test_live_snapshot_units_and_bounds(self):
        memory = resources.memory()
        self.assertTrue(0 <= memory["used"] <= memory["total"])
        self.assertTrue(0 <= memory["percent"] <= 100)
        previous, rows = resources.processes({}, 2)
        self.assertTrue(previous)
        self.assertLessEqual(len(rows), 7)
        self.assertTrue(all(row["cpu"] == 0 and row["memory"] >= 0 for row in rows))


if __name__ == "__main__":
    unittest.main()
