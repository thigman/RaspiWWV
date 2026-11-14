import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.output = self.root / "output"
        self.output.mkdir()
        self.stub("id", 'if [ "$1" = "-u" ]; then echo 1000; else echo root; fi')
        self.stub("crontab", 'printf "%s\\n" "$FAKE_CRONTAB"')
        self.stub("sudo", """
echo "$*" >> "$FAKE_OUTPUT/commands"
if [ "$1" = install ]; then cp "$4" "$FAKE_OUTPUT/$(basename "$5")"; fi
""")
        self.stub("fake-python", "exit 0")
        self.env = os.environ.copy()
        self.env.update({
            "PATH": f"{self.bin}:{self.env['PATH']}",
            "PYTHON": str(self.bin / "fake-python"),
            "FAKE_OUTPUT": str(self.output),
            "FAKE_CRONTAB": "",
        })

    def stub(self, name, body):
        path = self.bin / name
        path.write_text(f"#!/bin/sh\n{body}\n")
        path.chmod(0o755)

    def install(self, *args):
        return subprocess.run(
            [str(REPO / "installWWV.sh"), *args],
            env=self.env, text=True, capture_output=True,
        )

    def test_installs_independent_services_and_restarts_them(self):
        result = self.install("--oled")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, script in [("audio", "wwv_simulator.py"), ("oled", "clockOLED.py")]:
            unit = (self.output / f"raspiwwv-{name}.service").read_text()
            self.assertIn(f'ExecStart="{self.bin}/fake-python" -u "{REPO}/{script}"', unit)
            self.assertIn("Restart=always", unit)
            self.assertIn("StartLimitIntervalSec=0", unit)
            self.assertIn(f"systemctl restart raspiwwv-{name}.service",
                          (self.output / "commands").read_text())

    def test_legacy_reboot_job_stops_install_before_sudo(self):
        self.env["FAKE_CRONTAB"] = "@reboot /bin/bash ./runWWV.sh"
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("crontab -e", result.stderr)
        self.assertFalse((self.output / "commands").exists())


if __name__ == "__main__":
    unittest.main()
