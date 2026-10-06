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


if __name__ == "__main__":
    unittest.main()
