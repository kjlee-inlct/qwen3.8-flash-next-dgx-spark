from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"
BENCH = ROOT / "scripts" / "benchmark"


class ScriptLayoutTests(unittest.TestCase):
    def test_canonical_internal_helpers_exist(self) -> None:
        for relative in (
            "lib/state_file.py",
            "lib/release_manifest.py",
            "diagnostics/doctor-observability.sh",
            "diagnostics/collect-diagnostics.sh",
            "runtime/runtime-transition.sh",
            "runtime/preflight-runtime.sh",
            "runtime/service-runner.sh",
            "runtime/monitor-runtime.sh",
            "runtime/validate_runtime.py",
            "lifecycle/update-transition.sh",
            "lifecycle/bootstrap-release.sh",
            "lifecycle/qualify-release.sh",
            "model/model-profiles.sh",
            "model/inspect_model.py",
            "model/prepare_config.py",
            "benchmark/run.py",
            "benchmark/lib/common.py",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((SCRIPTS / relative).is_file())

    def test_compatibility_entry_points_target_canonical_helpers(self) -> None:
        expected = {
            "state_file.py": '"lib" / "state_file.py"',
            "release_manifest.py": '"lib" / "release_manifest.py"',
            "doctor-observability.sh": "diagnostics/doctor-observability.sh",
            "runtime-transition.sh": "runtime/runtime-transition.sh",
            "preflight-runtime.sh": "runtime/preflight-runtime.sh",
            "service-runner.sh": "runtime/service-runner.sh",
            "update-transition.sh": "lifecycle/update-transition.sh",
            "bootstrap-release.sh": "lifecycle/bootstrap-release.sh",
            "qualify-release.sh": "lifecycle/qualify-release.sh",
            "collect-diagnostics.sh": "diagnostics/collect-diagnostics.sh",
            "monitor-runtime.sh": "runtime/monitor-runtime.sh",
            "validate-runtime.py": 'with_name("runtime") / "validate_runtime.py"',
            "model-profiles.sh": "model/model-profiles.sh",
            "inspect-model.py": 'with_name("model") / "inspect_model.py"',
            "prepare-config.py": 'with_name("model") / "prepare_config.py"',
        }
        for name, target in expected.items():
            with self.subTest(name=name):
                text = (SCRIPTS / name).read_text(encoding="utf-8")
                self.assertIn(target, text)

    def test_benchmark_entry_and_helpers_are_separated(self) -> None:
        self.assertTrue((BENCH / "run.py").is_file())
        self.assertTrue((BENCH / "lib" / "common.py").is_file())
        compatibility = (BENCH / "common.py").read_text(encoding="utf-8")
        self.assertIn("lib.common", compatibility)
        readme = (SCRIPTS / "README.md").read_text(encoding="utf-8")
        self.assertIn("scripts/benchmark/run.py", readme)
        self.assertIn("scripts/bench-prefill.py", readme)
        compatibility = (ROOT / "bench" / "run.py").read_text(encoding="utf-8")
        self.assertIn('scripts" / "benchmark"', compatibility)

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

    def test_transition_compatibility_status_entry_points_work(self) -> None:
        runtime = subprocess.run(
            ["bash", str(SCRIPTS / "runtime-transition.sh"), "status"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        update = subprocess.run(
            ["bash", str(SCRIPTS / "update-transition.sh"), "status"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(runtime.returncode, 0, runtime.stderr)
        self.assertIn("TRANSACTION_STATE=idle", runtime.stdout)
        self.assertEqual(update.returncode, 0, update.stderr)
        self.assertIn("UPDATE_STATE=idle", update.stdout)

    def test_scripts_readme_documents_root_role_categories(self) -> None:
        readme = (SCRIPTS / "README.md").read_text(encoding="utf-8")
        for heading in (
            "## Top-level role map",
            "## Upstream provenance",
            "## Stable operator entry points",
            "## Compatibility entry points",
            "## Canonical internal categories",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, readme)
        for category in (
            "benchmark/",
            "diagnostics/",
            "lifecycle/",
            "lib/",
            "model/",
            "runtime/",
        ):
            with self.subTest(category=category):
                self.assertIn(category, readme)
        self.assertIn("the goal is not an empty `scripts/` root", readme)

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
            "runtime-transition.sh",
            "update-transition.sh",
        ):
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", readme)
                self.assertTrue((SCRIPTS / name).is_file())

    def test_upstream_derived_script_paths_are_preserved(self) -> None:
        readme = (SCRIPTS / "README.md").read_text(encoding="utf-8")
        self.assertIn("dolf3131/qwen3.8-flash-next-dgx-spark", readme)
        for name in (
            "Dockerfile.nv-mixed",
            "Dockerfile.skinny-gemm",
            "bench-prefill.py",
            "download-weights.sh",
            "patch-nv-mixed.py",
            "patch-skinny-gemm-tp1.py",
            "serve.sh",
        ):
            with self.subTest(name=name):
                self.assertTrue((SCRIPTS / name).is_file())
                self.assertIn(f"`{name}`", readme)


if __name__ == "__main__":
    unittest.main()
