"""Modular Wizard safe-navigation regression tests; no DGX interaction."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ModularWizardTests(unittest.TestCase):
    def run_case(self, home: Path, args: list[str], answers: str = "") -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "xdg")}
        env.pop("UI_LANG", None)
        env.pop("QWEN38_MODEL_ROOT", None)
        return subprocess.run(
            ["bash", str(ROOT / "wizard.sh"), *args],
            cwd=ROOT, env=env, input=answers,
            capture_output=True, text=True, check=False, timeout=20,
        )

    def test_status_never_claims_runtime_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_case(home, ["--status", "--lang", "en"])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Manifest: missing", result.stdout)
            self.assertIn("Runtime : NOT_PROBED", result.stdout)
            self.assertFalse((home / "xdg").exists())

    def test_main_menu_retries_bad_choice_and_exits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_case(home, ["--lang", "en"], "invalid\n0\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Invalid selection", result.stdout)
            self.assertFalse((home / "xdg").exists())

    def test_nested_back_is_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_case(home, ["--lang", "ko"], "3\n0\n4\n0\n5\n0\n6\n0\n8\n0\n0\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((home / "xdg").exists())

    def test_mazinb_evidence_menu_invalid_case_has_no_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_case(home, ["--lang", "ko"], "5\n5\ninvalid\n0\n0\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Invalid trial", result.stdout)
            self.assertFalse((home / "xdg").exists())

    def test_mazinb_status_and_menu_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_case(home, ["--lang", "en"], "5\n4\n0\n0\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("mazinb historical experiments", result.stdout)
            self.assertFalse((home / "xdg").exists())

    def test_evidence_numeric_selection_is_not_an_invalid_trial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bin_dir = home / "bin"
            bin_dir.mkdir()
            mock_bash = bin_dir / "bash"
            mock_bash.write_text(
                '#!/bin/sh\n'
                'if [ "$2" = evidence ]; then printf "MOCK_EVIDENCE=%s\\n" "$3"; exit 0; fi\n'
                'exit 73\n', encoding="utf-8",
            )
            mock_bash.chmod(0o700)
            env = {
                **os.environ, "HOME": str(home),
                "XDG_STATE_HOME": str(home / "xdg"),
                "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
            }
            for option, expected in (
                ("1", ["A"]), ("2", ["B"]), ("3", ["A", "B"]),
                ("B", ["B"]), ("0", []),
            ):
                with self.subTest(selection=option):
                    result = subprocess.run(
                        ["/bin/bash", str(ROOT / "wizard.sh"), "--lang", "en"],
                        cwd=ROOT, env=env, input=f"5\n5\n{option}\n0\n0\n",
                        text=True, capture_output=True, timeout=20, check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    reviewed = [
                        line.split("=", 1)[1] for line in result.stdout.splitlines()
                        if line.startswith("MOCK_EVIDENCE=")
                    ]
                    self.assertEqual(reviewed, expected)
                    self.assertNotIn("Invalid trial", result.stdout)
            self.assertFalse((home / "xdg").exists())

    def test_existing_historical_b_blocks_fresh_b_before_id_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bin_dir = home / "bin"
            bin_dir.mkdir()
            mock_docker = bin_dir / "docker"
            mock_docker.write_text(
                '#!/bin/sh\n'
                'if [ "$1" = inspect ] && [ "$4" = qwen38-mazinb-kv-b ]; then\n'
                '  printf "%064d\\n" 1\n'
                '  exit 0\n'
                'fi\n'
                'exit 77\n', encoding="utf-8",
            )
            mock_docker.chmod(0o700)
            env = {
                **os.environ, "HOME": str(home),
                "XDG_STATE_HOME": str(home / "xdg"),
                "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
            }
            result = subprocess.run(
                ["/bin/bash", str(ROOT / "wizard.sh"), "--lang", "en"],
                cwd=ROOT, env=env, input="5\n2\n0\n0\n",
                text=True, capture_output=True, timeout=20, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Historical B container already exists", result.stdout)
            self.assertNotIn("Re-enter complete predecessor Docker ID", result.stdout)
            self.assertFalse((home / "xdg").exists())

    def test_eof_aborts_before_default_choice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_case(Path(tmp), ["--lang", "en"])
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("Input stream closed (EOF)", result.stderr)

    def test_install_default_no_is_not_consent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_case(home, ["--lang", "en"], "1\n\n0\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((home / "xdg").exists())

    def test_nested_eof_also_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_case(Path(tmp), ["--lang", "en"], "3\n")
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("Input stream closed (EOF)", result.stderr)

    def test_malformed_manifest_blocks_installer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            state = home / "xdg" / "qwen38-spark"
            state.mkdir(parents=True)
            (state / "install.env").write_text("PHASE=complete\nMODEL_PROFILE=orcarouter\n", encoding="utf-8")
            result = self.run_case(home, ["--lang", "en"], "1\n0\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Manifest: invalid", result.stdout)
            self.assertIn("Invalid install manifest", result.stderr)

    def test_symlinked_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            state = home / "xdg" / "qwen38-spark"
            state.mkdir(parents=True)
            target = home / "not-a-manifest"
            target.write_text("PHASE=complete\n", encoding="utf-8")
            (state / "install.env").symlink_to(target)
            result = self.run_case(home, ["--status"])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Manifest: invalid", result.stdout)

    def test_unknown_flag_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_case(Path(tmp), ["--yes"])
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
