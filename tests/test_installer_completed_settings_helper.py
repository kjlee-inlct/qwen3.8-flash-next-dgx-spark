from __future__ import annotations

import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
HELPER = ROOT / "scripts" / "lib" / "install-completed-manager.sh"
WIZARD = ROOT / "scripts" / "lib" / "wizard-ui.sh"


class CompletedInstallSettingsHelperTests(unittest.TestCase):
    def test_helper_defaults_to_preview_and_delegates_live_apply(self) -> None:
        text = HELPER.read_text(encoding="utf-8")
        self.assertIn("INSTALL_COMPLETED_SETTINGS_PREVIEW_ONLY=1", text)
        self.assertIn("INSTALL_COMPLETED_SETTINGS_APPLY=1", text)
        self.assertIn("write_state complete", text)
        self.assertIn("settings-transition.sh", text)
        self.assertNotIn("scripts/lifecycle/", text)
        self.assertNotIn("manage-service.sh", text)
        self.assertNotIn("manage-proxy.sh", text)
        self.assertNotIn("profile-switch-transition.sh", text)
        self.assertNotIn("runtime-transition.sh", text)

    def test_wizard_loads_helper_only_for_installer(self) -> None:
        text = WIZARD.read_text(encoding="utf-8")
        self.assertIn('if [[ "${BASH_SOURCE[1]:-}" == */install.sh ]]; then', text)
        self.assertIn("install-completed-manager.sh", text)
        self.assertIn("install_completed_manager_step_hook", text)

    def test_settings_are_reapplied_before_normalized_plan(self) -> None:
        text = WIZARD.read_text(encoding="utf-8")
        hook = text.index("install_completed_manager_step_hook")
        finalize = text.index("install_plan_finalize", hook)
        self.assertLess(hook, finalize)

    def test_commit_failure_is_returned_after_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_file = root / "install.env"
            transition = root / "settings-transition.sh"
            recovered = root / "recovered"
            transition.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env bash",
                        "case \"$1\" in",
                        "  prepare) rm -f -- \"$2\"; exit 0 ;;",
                        "  apply) exit 0 ;;",
                        f"  commit) exit 42 ;;",
                        f"  recover) : > {shlex.quote(str(recovered))}; exit 0 ;;",
                        "  *) exit 2 ;;",
                        "esac",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            transition.chmod(0o755)

            script = "\n".join(
                [
                    f"source {shlex.quote(str(HELPER))}",
                    f"STATE_FILE={shlex.quote(str(state_file))}",
                    'STATE_WRITE_FILE="$STATE_FILE"',
                    f"INSTALL_COMPLETED_SETTINGS_TRANSITION={shlex.quote(str(transition))}",
                    "INSTALL_COMPLETED_SETTINGS_APPLY=1",
                    "DRY_RUN=0",
                    "START=0",
                    "UI_LANG=en",
                    "die() { printf 'ERROR: %s\\n' \"$*\" >&2; return 99; }",
                    "write_state() { printf 'PHASE=%s\\n' \"$1\" >\"$STATE_WRITE_FILE\"; }",
                    "install_completed_execute_settings_transaction",
                ]
            )
            result = subprocess.run(
                ["bash", "-c", script],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 42, result.stderr)
            self.assertTrue(recovered.exists())
            self.assertFalse(Path(str(state_file) + ".settings-input").exists())


if __name__ == "__main__":
    unittest.main()
