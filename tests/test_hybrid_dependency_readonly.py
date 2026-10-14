"""Synthetic dependency audit tests; no physical DGX or Docker mutation."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/wizard/hybrid-dependency-readonly.py"
spec = importlib.util.spec_from_file_location("hybrid_dependency_readonly", SCRIPT)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class HybridDependencyAuditTests(unittest.TestCase):
    def test_current_root_and_other_root(self):
        root = Path("/home/inlc/Workspace/llm/project/models")
        stage = audit.STAGES["h6"]
        self.assertEqual(audit.match_mount_source(str(root / stage), root),
                         ("h6", "CURRENT_ROOT"))
        self.assertEqual(audit.match_mount_source("/home/inlc/models/" + stage, root),
                         ("h6", "ALIAS_OR_OTHER_ROOT"))
        self.assertEqual(audit.match_mount_source(str(root / stage / "part.safetensors"), root),
                         ("h6", "CURRENT_ROOT"))
        self.assertIsNone(audit.match_mount_source("/tmp/other-model", root))
        self.assertIsNone(audit.match_mount_source("relative/path/" + stage, root))

    def test_h7_h20_registry_aliases_are_protected(self):
        refs = audit.registry_references(Path("/tmp/read-only-hybrid-models"))
        names = {(profile, stage) for profile, stage, _ in refs}
        self.assertIn(("hybrid-h7-group-metadata", "h6"), names)
        self.assertIn(("hybrid-h20-modelopt-convert-diag", "h6"), names)
        self.assertFalse(any(profile == "hybrid-h6-w4a16" for profile, *_ in refs))

    def test_bad_sha_is_rejected_without_host_mutation(self):
        result = subprocess.run(
            ["python3", "-B", str(SCRIPT),
             "--models-root", str(ROOT), "--expected-sha", "wrong"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("HYBRID_DELETION_AUTHORIZED=NO", result.stderr)

    def test_script_excludes_destructive_operations(self):
        src = SCRIPT.read_text(encoding="utf-8")
        for required in ("docker", "inspect", "PROTECTED_PROFILE_REFERENCE=",
                         "DOCKER_STAGE_REFERENCE=", "HYBRID_DELETION_AUTHORIZED=NO"):
            self.assertIn(required, src)
        for forbidden in ("docker rm", "docker start", "docker run",
                          "systemctl start", "rmtree(", "unlink(", "rm -rf",
                          "git reset", "swapoff", "os.remove"):
            self.assertNotIn(forbidden, src)

if __name__ == "__main__":
    unittest.main()
