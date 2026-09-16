from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


class ScriptLayoutTests(unittest.TestCase):
    def test_canonical_internal_helpers_exist(self) -> None:
        for relative in (
            "lib/state_file.py",
            "lib/release_manifest.py",
            "diagnostics/doctor-observability.sh",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((SCRIPTS / relative).is_file())

    def test_compatibility_entry_points_target_canonical_helpers(self) -> None:
        state = (SCRIPTS / "state_file.py").read_text(encoding="utf-8")
        manifest = (SCRIPTS / "release_manifest.py").read_text(encoding="utf-8")
        observability = (SCRIPTS / "doctor-observability.sh").read_text(encoding="utf-8")
        self.assertIn('"lib" / "state_file.py"', state)
        self.assertIn('"lib" / "release_manifest.py"', manifest)
        self.assertIn("diagnostics/doctor-observability.sh", observability)

    def test_state_parser_compatibility_entry_point_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "qualification.env"
            state_file.write_text(
                "\n".join(
                    [
                        "QUALIFICATION_SCHEMA_VERSION=1",
                        "QUALIFIED_RELEASE=" + "a" * 40,
                        "QUALIFIED_AT=2026-09-16T01:00:00Z",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                ["python3", str(SCRIPTS / "state_file.py"), "qualification", str(state_file)],
                cwd=ROOT,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b"QUALIFIED_RELEASE", result.stdout)

    def test_layout_policy_preserves_stable_entry_points(self) -> None:
        readme = (SCRIPTS / "README.md").read_text(encoding="utf-8")
        for name in (
            "doctor.sh",
            "serve.sh",
            "manage-service.sh",
            "manage-proxy.sh",
            "manage-swap.sh",
            "release-manager.sh",
            "update-release.sh",
        ):
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", readme)
                self.assertTrue((SCRIPTS / name).is_file())


if __name__ == "__main__":
    unittest.main()
