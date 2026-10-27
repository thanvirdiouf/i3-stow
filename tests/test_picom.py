# SPDX-License-Identifier: GPL-3.0-or-later
"""Check compositor selection without starting a display server or compositor."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / ".config/picom/start.sh"


class CompositorLauncher(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=str(self.bin) + ":/usr/bin:/bin")

    def executable(self, path, source):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"#!{sys.executable}\n" + source)
        path.chmod(0o755)

    def picom(self, path, label, version="v13"):
        self.executable(path, f"import json, sys\n"
                        f"if sys.argv[1:] == ['--version']: print({version!r}); sys.exit(0)\n"
                        f"print(json.dumps([{label!r}, *sys.argv[1:]]))\n")

    def launch(self):
        result = subprocess.run(["sh", str(LAUNCHER), "--daemon"], env=self.env,
                                capture_output=True, text=True, check=True, timeout=5)
        return json.loads(result.stdout)

    def test_path_picom_uses_nixgl_and_forwards_config_and_arguments(self):
        modern = self.bin / "picom"
        self.executable(modern,
                        "import json, os, sys\n"
                        "if sys.argv[1:] == ['--version']: print('v13'); sys.exit(0)\n"
                        "assert os.environ.get('PICOM_TEST_GL') == 'enabled'\n"
                        "print(json.dumps(['upstream', *sys.argv[1:]]))\n")
        self.executable(self.bin / "nixGL",
                        "import os, sys\nos.environ['PICOM_TEST_GL'] = 'enabled'\n"
                        "os.execv(sys.argv[1], sys.argv[1:])\n")
        result = self.launch()
        self.assertEqual(result, ["upstream", "--config", str(LAUNCHER.parent / "picom.conf"), "--daemon"])

    def test_path_picom_without_nixgl_runs_directly(self):
        self.picom(self.bin / "picom", "distribution")
        self.assertEqual(self.launch(),
                         ["distribution", "--config", str(LAUNCHER.parent / "picom.conf"), "--daemon"])

    def test_first_picom_on_path_wins(self):
        preferred = self.base / "profile/bin"
        self.picom(preferred / "picom", "profile")
        self.picom(self.bin / "picom", "distribution")
        self.env["PATH"] = str(preferred) + ":" + self.env["PATH"]
        self.assertEqual(self.launch()[0], "profile")

    def test_distribution_v10_uses_legacy_config(self):
        self.picom(self.bin / "picom", "distribution", version="v10")
        self.assertEqual(self.launch(),
                         ["distribution", "--config", str(LAUNCHER.parent / "legacy.conf"), "--daemon"])

    def test_unknown_version_fails_before_starting_compositor(self):
        self.picom(self.bin / "picom", "unknown", version="unknown")
        result = subprocess.run(["sh", str(LAUNCHER)], env=self.env,
                                capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cannot determine Picom version", result.stderr)


if __name__ == "__main__":
    unittest.main()
