"""Regressions for durable wizard-first mission and historical model scope.

Source/read-only verification only; no installer, Docker or GPU execution.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MISSION = ROOT / "docs/PROJECT-MISSION-AND-MODEL-SCOPE.md"
HANDOFF = ROOT / "docs/SESSION-HANDOFF-PROMPT.md"
REGISTRY = ROOT / "scripts/model/model-profiles.sh"

ORIGINAL_REPOS = (
    "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
    "nvidia/Qwen3.8-Flash-Next-NVFP4",
    "mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4",
    "lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE",
)


class ProjectMissionDocsTests(unittest.TestCase):
    def test_original_four_and_later_hybrid_distinguished(self) -> None:
        mission = MISSION.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        for name in ORIGINAL_REPOS:
            with self.subTest(name=name):
                self.assertIn(name, mission)
                self.assertIn(name, handoff)
        self.assertIn("4 original + 1 later-added Hybrid", mission)
        self.assertIn("orcarouter-hybrid", mission)
        self.assertIn("orcarouter-hybrid", handoff)
        self.assertIn("H38", mission)
        self.assertIn("not a sixth wizard model", mission)

    def test_wizard_first_goal_and_entry_points(self) -> None:
        mission = MISSION.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("Primary product goal (P0)", mission)
        self.assertIn("terminal wizard", mission)
        self.assertIn("./install.sh", mission)
        self.assertIn("./uninstall.sh", mission)
        self.assertIn("PROJECT-MISSION-AND-MODEL-SCOPE.md", handoff)
        self.assertIn("위자드 목표 복구", handoff)
        self.assertIn("lychee888", handoff)

    def test_current_registry_shows_three_originals_plus_hybrid(self) -> None:
        registry = REGISTRY.read_text(encoding="utf-8")
        for name in ORIGINAL_REPOS:
            with self.subTest(name=name):
                self.assertIn(name, registry)
        self.assertIn("list_model_profiles()", registry)
        self.assertIn("orcarouter nvidia mazinb orcarouter-hybrid", registry)
        self.assertIn("list_model_candidates()", registry)
        self.assertIn('PROFILE_STATUS="planned"', registry)
        self.assertIn("PROFILE_INSTALLABLE=0", registry)


if __name__ == "__main__":
    unittest.main()
