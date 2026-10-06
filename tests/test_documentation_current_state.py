from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class DocumentationCurrentStateTests(unittest.TestCase):
    def test_current_status_entry_point_exists_and_preserves_strict_rm_semantics(self) -> None:
        text = read("docs/CURRENT-STATUS.md")
        self.assertIn("canonical short-form status entry point", text)
        self.assertIn("FUNCTIONAL and HOST-STABILITY classifications are separate", text)
        self.assertIn("NV_ERR_NO_MEMORY", text)
        self.assertIn("R9–R32 allocator/localization closure", text)
        self.assertIn("not a proven discriminator for RM failure", text)
        self.assertIn("Last synchronized: 2026-10-06", text)
        self.assertIn("The version on `main` is authoritative", text)
        self.assertIn("would make that marker stale as soon as it is merged", text)

    def test_root_readme_tracks_current_managed_status(self) -> None:
        text = read("README.md")
        self.assertIn("[docs/CURRENT-STATUS.md](docs/CURRENT-STATUS.md)", text)
        self.assertIn("16 GiB managed KV resilience default", text)
        self.assertIn("current strict classification: FUNCTIONAL PASS / HOST-STABILITY FAIL", text)
        self.assertIn("safety heuristic, not a proven RM-failure discriminator", text)
        self.assertIn("historical/manual NVIDIA path", text)
        self.assertNotIn("mazinb             experimental / installable / clean managed DGX lifecycle pending", text)
        self.assertNotIn("its real download/image-build/systemd/API-ready lifecycle remains pending", text)
        self.assertNotIn("2026-09-29 host-stability repair gate PASS", text)
        self.assertNotIn("That closes the reproduced failure mode", text)
        self.assertNotIn("24 GiB of pinned KV", text)

    def test_runtime_readme_does_not_call_24gib_the_current_mazinb_default(self) -> None:
        text = read("scripts/runtime/README.md")
        self.assertIn("16 GiB KV cache (`17179869184` bytes)", text)
        self.assertIn("historical 24 GiB control", text)
        self.assertNotIn("current mazinb default/control", text)
        self.assertNotIn("current mazinb default", text.lower())
        self.assertNotIn("git switch docs/live-profile-switch-acceptance-20260930", text)

    def test_model_and_architecture_docs_do_not_leave_mazinb_activation_pending(self) -> None:
        architecture = read("docs/ARCHITECTURE.md")
        model = read("scripts/model/README.md")

        for text in (architecture, model):
            self.assertIn("FUNCTIONAL PASS / HOST-STABILITY FAIL", text)
            self.assertIn("R23", text)
            self.assertNotIn("live managed activation pending", text.lower())
            self.assertNotIn("Actual live profile activation", text)

        self.assertNotIn("lower-level Linux zone/migratetype/buddy reason", architecture)

    def test_evidence_index_is_post_merge(self) -> None:
        text = read("scripts/benchmark/evidence/README.md")
        self.assertIn("5b6ba67eddf1902cdf2daa17ec30f6e043e26fa6", text)
        self.assertIn("post-merge canonical repository state", text)
        self.assertNotIn("PR #244 remains intentionally open", text)
        self.assertNotIn("must not be merged before mitigation", text)

    def test_operations_describes_monitor_as_heuristic_not_host_classifier(self) -> None:
        text = read("OPERATIONS.md")
        self.assertIn("implemented safety heuristic", text)
        self.assertIn("false-positive protected stop", text)
        self.assertIn("not as HOST-STABILITY evidence by itself", text)
        self.assertNotIn("This preserves the observed healthy large-checkpoint shard-loading transient", text)

    def test_historical_execution_documents_are_explicitly_scoped(self) -> None:
        r28 = read("scripts/benchmark/evidence/orcarouter-r28-static-dgx-next-steps-20261005.md")
        report = read("scripts/benchmark/evidence/nvidia-gb10-rm-sysmem-report-draft-20261002.md")
        closure = read("scripts/benchmark/evidence/branch-closure-profile-switch-acceptance-20261006.md")
        r23_r32 = read("scripts/benchmark/evidence/orcarouter-r23-r32-allocation-localization-closure-20261006.md")

        self.assertIn("Historical / superseded execution instruction", r28)
        self.assertIn("R28 was subsequently executed", r28)
        self.assertIn("HISTORICAL R9-ERA INTERNAL DRAFT", report)
        self.assertIn("R11 localized node0 Normal-zone", report)
        self.assertIn("SQUASH-MERGED INTO `main`", closure)
        self.assertIn("5b6ba67eddf1902cdf2daa17ec30f6e043e26fa6", closure)
        self.assertIn("PR #244 is merged", r23_r32)

    def test_registry_and_docs_agree_mazinb_is_installable_experimental(self) -> None:
        registry = read("scripts/model/model-profiles.sh")
        architecture = read("docs/ARCHITECTURE.md")
        model = read("scripts/model/README.md")

        self.assertIn("PROFILE_STATUS=\"experimental\"", registry)
        self.assertIn("PROFILE_INSTALLABLE=1", registry)
        self.assertIn("Optional mazinb profile; 16 GiB managed KV resilience mitigation validated", registry)
        self.assertIn("mazinb — experimental/installable", architecture)
        self.assertIn("mazinb", model)
        self.assertIn("16 GiB", model)

    def test_state_file_docs_include_runtime_transition_strict_parser(self) -> None:
        text = read("STATE-FILES.md")
        self.assertIn("runtime-transition.env", text)
        self.assertIn("dedicated `runtime-transition` schema", text)
        self.assertIn("malformed state fails closed", text)

    def test_script_maps_include_profile_switch_lifecycle_surface(self) -> None:
        layout = read("scripts/README.md")
        lifecycle = read("scripts/lifecycle/README.md")

        self.assertIn("profile-switch-transition.sh", layout)
        self.assertIn("lifecycle/profile-switch-transition.sh", layout)
        self.assertIn("profile-switch transaction logic", lifecycle)
        self.assertIn("`profile-switch-transition.sh`", lifecycle)

    def test_installable_mazinb_download_docs_do_not_require_candidate_flag(self) -> None:
        text = read("scripts/README.md")
        self.assertIn("Installable profiles such as `mazinb` no longer require `--candidate`", text)
        self.assertIn("MODEL_PROFILE=mazinb ./scripts/download-weights.sh --check", text)
        self.assertIn("MODEL_PROFILE=mazinb ./scripts/download-weights.sh\n", text)
        self.assertNotIn("MODEL_PROFILE=mazinb ./scripts/download-weights.sh --candidate --check", text)


if __name__ == "__main__":
    unittest.main()
