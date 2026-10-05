from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SERVE = ROOT / "scripts" / "serve.sh"


class MazinbManagedKvDefaultTests(unittest.TestCase):
    def test_mazinb_uses_promoted_16_gib_kv_default(self) -> None:
        text = SERVE.read_text(encoding="utf-8")
        start = text.index("  mazinb)\n")
        end = text.index("  orcarouter-hybrid)\n", start)
        block = text[start:end]

        self.assertIn("DEFAULT_KV_MEM=17179869184", block)
        self.assertNotIn("DEFAULT_KV_MEM=25769803776", block)
        self.assertIn("16 GiB passed strict readiness/soak/host checks", block)
        self.assertIn("24 GiB reproduced RM NV_ERR_NO_MEMORY", block)

    def test_hybrid_kv_default_is_unchanged(self) -> None:
        text = SERVE.read_text(encoding="utf-8")
        start = text.index("  orcarouter-hybrid)\n")
        end = text.index("  *) echo", start)
        block = text[start:end]

        self.assertIn("DEFAULT_KV_MEM=25769803776", block)


if __name__ == "__main__":
    unittest.main()
