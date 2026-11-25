# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression coverage for desktop controls, lock handoff, and resource sampling."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / ".config/quickshell"


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SHELL / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


resources = load_module("resources", "resources.py")


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
                        LOCK_TEST_CAPTURE=str(self.base / "result.json"))
        fake_locker = self.bin / "i3lock"
        fake_locker.write_text(f"#!{sys.executable}\n" + """import json, os, sys
from pathlib import Path
result = {'args': sys.argv[1:]}
if 'XSS_SLEEP_LOCK_FD' in os.environ:
    result['sleep_fd_open'] = os.fstat(int(os.environ['XSS_SLEEP_LOCK_FD'])).st_mode > 0
Path(os.environ['LOCK_TEST_CAPTURE']).write_text(json.dumps(result))
""")
        fake_locker.chmod(0o755)

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


class ResourceSnapshots(unittest.TestCase):
    def test_nvidia_units_and_missing_values(self):
        rows = resources.parse_nvidia_gpus(
            '00000000:01:00.0, NVIDIA GeForce GTX 1650 Ti, 14, 47, 4096, 47\n'
            '00000000:02:00.0, "NVIDIA GPU, secondary", [Not Supported], N/A, 8192, N/A\n'
            'malformed row\n')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["utilization"], 14)
        self.assertEqual(rows[0]["memoryUsed"], 47 * 1024**2)
        self.assertEqual(rows[0]["memoryTotal"], 4 * 1024**3)
        self.assertEqual(rows[0]["temperature"], 47)
        self.assertIsNone(rows[1]["utilization"])
        self.assertIsNone(rows[1]["memoryUsed"])
        self.assertIsNone(rows[1]["temperature"])
        for invalid in ["nan", "inf", "-1", "[N/A]", "101"]:
            self.assertIsNone(resources.gpu_number(invalid, 100))

    def test_gpu_timeout_does_not_break_sampler(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(resources.shutil, "which", return_value="/usr/bin/nvidia-smi"), \
             patch.object(resources.subprocess, "run", side_effect=subprocess.TimeoutExpired("nvidia-smi", 1)):
            self.assertEqual(resources.gpu_stats(Path(directory)), [])

    def test_amd_sysfs_gpu_and_unreadable_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            device = root / "card0/device"
            hwmon = device / "hwmon/hwmon0"
            hwmon.mkdir(parents=True)
            for name, value in {"vendor": "0x1002", "product_name": "AMD Radeon fixture",
                                "gpu_busy_percent": "32", "mem_info_vram_used": "1073741824",
                                "mem_info_vram_total": "8589934592"}.items():
                (device / name).write_text(value)
            (hwmon / "temp1_input").write_text("52000")
            with patch.object(resources.shutil, "which", return_value=None):
                gpu = resources.gpu_stats(root)[0]
                self.assertEqual(gpu["utilization"], 32)
                self.assertEqual(gpu["memoryTotal"], 8 * 1024**3)
                self.assertEqual(gpu["temperature"], 52)
                (device / "gpu_busy_percent").write_text("not available")
                self.assertIsNone(resources.gpu_stats(root)[0]["utilization"])

    def test_temperatures_classify_sensors_and_skip_invalid_readings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures = [("coretemp", {"temp1_input": "49000", "temp2_input": "51000", "temp3_input": "invalid"}),
                        ("nvme", {"temp1_label": "Composite", "temp1_input": "48850", "temp2_input": "99000"}),
                        ("nvme", {"temp1_label": "Composite", "temp1_input": "52000"}),
                        ("pch_cometlake", {"temp1_input": "53000"}),
                        ("amdgpu", {"temp1_input": "47000"}),
                        ("iwlwifi_1", {"temp1_input": "70000"})]
            for index, (name, files) in enumerate(fixtures):
                device = root / f"hwmon{index}"
                device.mkdir()
                (device / "name").write_text(name)
                for filename, value in files.items():
                    (device / filename).write_text(value)
            self.assertEqual(resources.temperatures(root),
                             {"cpu": 51, "gpu": 47, "storage": 52, "chipset": 53})
            self.assertEqual(resources.temperatures(root / "missing"),
                             {"cpu": None, "gpu": None, "storage": None, "chipset": None})

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
