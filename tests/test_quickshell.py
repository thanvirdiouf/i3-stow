# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression coverage for desktop controls, lock handoff, and resource sampling."""
import json
import os
import select
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / ".config/quickshell"


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
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.root = Path(directory.name)
        cls.proc, cls.sys = cls.root / "proc", cls.root / "sys"
        cls.binary = cls.root / "resources"
        flags = subprocess.check_output(["pkg-config", "--cflags", "--libs", "glib-2.0"], text=True).split()
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", f'-DPROC_ROOT="{cls.proc}"',
                        f'-DSYS_ROOT="{cls.sys}"', str(SHELL / "resources.c"), "-o", cls.binary,
                        *flags, "-lm"], check=True)

    def setUp(self):
        for path in (self.proc, self.sys, self.root / "bin"):
            path.mkdir()
            self.addCleanup(shutil.rmtree, path)
        self.env = dict(os.environ, PATH=f"{self.root}/bin:/usr/bin:/bin")
        self.write(self.proc / "meminfo", "MemTotal: 1000 kB\nMemAvailable: 250 kB\nSwapTotal: 100 kB\nSwapFree: 40 kB")
        self.write(self.proc / "stat", "cpu 100 0 0 100 0 0 0 0\ncpu0 100 0 0 100 0 0 0 0\n")
        self.write(self.proc / "net/dev", "lo: 123 0 0 0 0 0 0 0 123\neth0: 300 0 0 0 0 0 0 0 200")
        self.write(self.proc / "uptime", "123.5 100")
        self.fake_smi("exit 1")

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def fake_smi(self, body):
        path = self.root / "bin/nvidia-smi"
        self.write(path, "#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def hwmon(self, index, name, files):
        device = self.sys / f"class/hwmon/hwmon{index}"
        for field, value in {"name": name, **files}.items():
            self.write(device / field, value)

    def sampler(self, *args):
        proc = subprocess.Popen([self.binary, *args], stdout=subprocess.PIPE, env=self.env, text=True)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.wait, 3)
        self.addCleanup(proc.terminate)
        return proc

    def sample(self, process):
        self.assertTrue(select.select([process.stdout], [], [], 5)[0], "sampler timed out")
        return json.loads(process.stdout.readline())

    def test_nvidia_units_and_unavailable_values(self):
        self.fake_smi("""printf '%s\\n' 'pci0, NVIDIA GTX, 14, 47, 4096, 47' 'pci1, "NVIDIA GPU, two", N/A, nan, 8192, N/A' 'malformed'""")
        sample = self.sample(self.sampler())
        a, b = sample["gpus"]
        self.assertEqual((a["id"], a["utilization"], a["memoryUsed"], a["memoryTotal"], a["temperature"]),
                         ("pci0", 14, 47 * 1024**2, 4096 * 1024**2, 47))
        self.assertEqual(b["name"], "NVIDIA GPU, two")
        self.assertIsNone(b["utilization"])
        self.assertIsNone(b["memoryUsed"])
        self.assertIsNone(b["temperature"])
        self.assertEqual(sample["temperatures"]["gpu"], 47)

    def test_gpu_timeout_does_not_stop_monitor(self):
        self.fake_smi("exec sleep 30")
        sample = self.sample(self.sampler())
        self.assertEqual(sample["gpus"], [])
        self.assertEqual(sample["memory"]["percent"], 75)

    def test_amd_sysfs_gpu_and_invalid_readings(self):
        dev = self.sys / "class/drm/card0/device"
        for field, value in {"vendor": "0x1002", "product_name": "AMD fixture", "gpu_busy_percent": "32",
                             "mem_info_vram_used": "1073741824", "mem_info_vram_total": "8589934592",
                             "hwmon/hwmon0/temp1_input": "52000"}.items():
            self.write(dev / field, value)
        proc = self.sampler()
        gpu, = self.sample(proc)["gpus"]
        self.assertEqual((gpu["name"], gpu["utilization"], gpu["memoryTotal"], gpu["temperature"]),
                         ("AMD fixture", 32, 8589934592, 52))
        self.write(dev / "gpu_busy_percent", "101")
        self.assertIsNone(self.sample(proc)["gpus"][0]["utilization"])

    def test_temperatures_only_use_recognized_sensors(self):
        self.hwmon(0, "coretemp", {"temp1_input": "51000"})
        self.hwmon(1, "nvme", {"temp1_label": "Composite", "temp1_input": "48850", "temp2_input": "99000"})
        self.hwmon(2, "pch_cometlake", {"temp1_input": "53000"})
        self.hwmon(3, "amdgpu", {"temp1_input": "47000"})
        self.hwmon(4, "iwlwifi_1", {"temp1_input": "90000"})
        self.assertEqual(self.sample(self.sampler())["temperatures"],
                         {"cpu": 51, "gpu": 47, "storage": 48.85, "chipset": 53})

    def test_summary_groups_smt_threads_and_matches_socket_sensors(self):
        marker = self.root / "unexpected-smi"
        self.fake_smi(f"touch '{marker}'")
        for cpu, socket in ((0, 0), (1, 0), (2, 1)):
            topo = self.sys / f"devices/system/cpu/cpu{cpu}/topology"
            self.write(topo / "physical_package_id", str(socket))
            self.write(topo / "core_id", "0")
            if cpu != 1:
                self.hwmon(socket, "coretemp", {"temp1_label": f"Package id {socket}", "temp1_input": "62000",
                                                "temp2_label": "Core 0", "temp2_input": "45000" if socket == 0 else "bad"})
        def cpu_stat(busy, idle):
            rows = [("cpu", sum(busy), sum(idle)), *((f"cpu{i}", b, d) for i,(b,d) in enumerate(zip(busy,idle)))]
            self.write(self.proc / "stat", "".join(f"{name} {b} 0 0 {d} 0 0 0 0\n" for name,b,d in rows))
        cpu_stat([100]*3, [100]*3)
        proc = self.sampler("--summary")
        self.sample(proc)
        cpu_stat([200, 100, 150], [100, 200, 150])
        result = self.sample(proc)
        self.assertEqual((result["cpu"], result["ram"], result["cpuSensor"]), (50, 75, 62))
        self.assertEqual(result["cores"], [
            {"label": "Socket 0 · Core 0", "usage": 50, "temperature": 45,
             "threads": [{"id": 0, "usage": 100}, {"id": 1, "usage": 0}]},
            {"label": "Socket 1 · Core 0", "usage": 50, "temperature": None,
             "threads": [{"id": 2, "usage": 50}]},
        ])
        self.assertFalse(marker.exists())

    def test_full_monitor_memory_network_and_process_deltas(self):
        def counters(ticks, rx, start=100):
            fields = ["0"] * 22
            fields[0], fields[11], fields[19], fields[21] = "S", str(ticks), str(start), "16"
            self.write(self.proc / "123/stat", '123 (strange "name") ' + " ".join(fields))
            self.write(self.proc / "net/dev", f"lo: 9 0 0 0 0 0 0 0 9\neth0: {rx} 0 0 0 0 0 0 0 200")
        counters(50, 300)
        proc = self.sampler()
        first = self.sample(proc)
        self.assertEqual(first["memory"], {"total": 1024000, "used": 768000, "percent": 75,
                                          "swapTotal": 102400, "swapUsed": 61440})
        self.assertEqual(first["interfaces"], ["eth0"])
        self.assertEqual(first["processes"][0]["name"], 'strange "name"')
        self.assertEqual(first["processes"][0]["cpu"], 0)
        counters(150, 2300)
        later = self.sample(proc)
        self.assertGreater(later["rx"], 0)
        self.assertGreater(later["processes"][0]["cpu"], 0)
        counters(200, 2300, start=200)
        self.assertEqual(self.sample(proc)["processes"][0]["cpu"], 0)


if __name__ == "__main__":
    unittest.main()
