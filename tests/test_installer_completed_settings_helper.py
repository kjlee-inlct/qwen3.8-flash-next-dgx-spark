from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
HELPER = ROOT / "scripts" / "lib" / "install-completed-manager.sh"
WIZARD = ROOT / "scripts" / "lib" / "wizard-ui.sh"


class CompletedInstallSettingsHelperTests(unittest.TestCase):
    def test_helper_is_preview_only_and_non_persistent(self) -> None:
        text = HELPER.read_text(encoding="utf-8")
        self.assertIn("DRY_RUN=1", text)
        self.assertIn("INSTALL_COMPLETED_SETTINGS_PREVIEW_ONLY=1", text)
        self.assertNotIn("write_state ", text)
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


if __name__ == "__main__":
    unittest.main()
