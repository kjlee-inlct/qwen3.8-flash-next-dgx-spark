"""Fixture-only vLLM/SGLang pinned model-engine subtree proof boundaries."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/model/inspect_catplusplus_engine_sources.py"
spec = importlib.util.spec_from_file_location("catplusplus_engine_inventory", SCRIPT)
assert spec and spec.loader
MOD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MOD)


def fixture():
    return [
        {"path": "extra/packages/vllm", "type": "directory"},
        {"path": "extra/packages/vllm/vllm/model_executor/qwen4_exp.py", "type": "file", "size": 250},
        {"path": "extra/packages/sglang", "type": "directory"},
        {"path": "extra/packages/sglang/python/sglang/srt/qwen4_exp.py", "type": "file", "size": 350},
        {"path": "extra/packages/vllm-qwen4_exp_sm110.bundle", "type": "file", "size": 30000},
        {"path": "extra/packages/sglang-qwen4_exp_sm110.bundle", "type": "file", "size": 31000},
    ]


class DualEngineInventoryTests(unittest.TestCase):
    def test_claimed_both_engines_metadata_never_attests_actual_functions(self):
        a = MOD.audit(fixture())
        self.assertEqual(a["revision"], MOD.REVISION)
        self.assertEqual(a["vllm_files"], 1)
        self.assertEqual(a["sglang_files"], 1)
        self.assertTrue(a["vllm_bundle_file_claim_matched"])
        self.assertTrue(a["sglang_bundle_file_claim_matched"])
        self.assertEqual(a["vllm_known_subtree_size_bytes"], 250)
        self.assertEqual(a["sglang_known_subtree_size_bytes"], 350)
        for key in ("content_integrity", "engine_impl", "mx_qkvz_scale_consumed",
                    "nvfp4_experts", "fp8_ple_offload", "gb10_sm121"):
            self.assertTrue(str(a[key]).startswith("NOT_"))
        self.assertEqual(a["live_admission"], "BLOCKED")
        self.assertFalse(a["checkpoint_download"])
        self.assertFalse(a["docker_or_gpu"])

    def test_unknown_tree_does_not_become_false_engine_proof(self):
        a = MOD.audit([{"path": "extra/packages/docs/vllm_notes.txt",
                        "type": "file", "size": 1}])
        self.assertEqual(a["vllm_files"], 0)
        self.assertEqual(a["sglang_files"], 0)
        self.assertFalse(a["vllm_bundle_file_claim_matched"])

    def test_scope_and_pagination_are_fail_closed(self):
        base = MOD.ROOT_URL + "?" + MOD.BASE_QUERY
        MOD.check_url(base)
        MOD.check_url(base + "&cursor=safe123")
        for unsafe in (
            "http://huggingface.co" + MOD.API_PATH + "?" + MOD.BASE_QUERY,
            "https://evil.invalid" + MOD.API_PATH + "?" + MOD.BASE_QUERY,
            MOD.ROOT_URL.replace(MOD.REVISION, "main") + "?" + MOD.BASE_QUERY,
            base + "&path=model.safetensors",
            base + "&limit=1",
            base + "&cursor=",
            base + "&cursor=a&cursor=b",
        ):
            with self.subTest(unsafe=unsafe), self.assertRaises(
                    MOD.EngineMetadataBlocked):
                MOD.check_url(unsafe)
        with self.assertRaisesRegex(MOD.EngineMetadataBlocked, "REDIRECT"):
            MOD.NoRedirect().redirect_request(None, None, 307, "", {},
                                             "https://bad.example/file")

    def test_path_traversal_duplicates_and_unexpected_type_blocked(self):
        for rows in (
            fixture() + [fixture()[1]],
            [{"path": "extra/packages/vllm/../bad.py",
              "type": "file", "size": 0}],
            [{"path": "experts-layer00.safetensors", "type": "file", "size": 8}],
            [{"path": "extra/packages/vllm/x.py", "type": "symbolic_link"}],
            [{"path": "extra/packages/vllm/x.py", "type": "file", "size": -1}],
        ):
            with self.subTest(rows=rows), self.assertRaises(
                    MOD.EngineMetadataBlocked):
                MOD.audit(rows)

    def test_pinned_get_accepts_exact_metadata_endpoint_and_limits_body(self):
        fake = fixture()
        used = []
        class FakeReply:
            status = 200
            headers = {}
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self, n):
                used.append(("read_bound", n))
                return json.dumps(fake).encode()
        class FakeClient:
            def open(self, request, timeout):
                used.append(("url", request.full_url, request.get_method(), timeout))
                return FakeReply()
        with mock.patch.object(MOD.urllib.request, "build_opener",
                               return_value=FakeClient()):
            data = MOD.tree()
        self.assertEqual(data, fake)
        self.assertEqual(used[0], ("url", MOD.ROOT_URL + "?" + MOD.BASE_QUERY,
                                   "GET", 30))
        self.assertEqual(used[1], ("read_bound", MOD.MAX_PAGE_BYTES + 1))

    def test_offline_cli_inspects_no_host_and_refuses_engine_admission(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "sample.json"
            path.write_text(json.dumps(fixture()), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "inventory",
                 "--offline-json", str(path)], capture_output=True,
                text=True, check=False, timeout=10, cwd=ROOT)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("CATPLUSPLUS_ENGINES_VLLM_FILES=1", proc.stdout)
            self.assertIn("CATPLUSPLUS_ENGINES_LIVE_GPU_BENCH_ADMISSION=BLOCKED",
                          proc.stdout)
            self.assertIn("CATPLUSPLUS_ENGINES_SOURCE_CONTENT=NOT_READ",
                          proc.stdout)
            self.assertEqual(sorted(p.name for p in Path(root).iterdir()),
                             ["sample.json"])

    def test_source_never_fetches_bundle_weight_or_runs_shell(self):
        s = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("subprocess.", "os.system(", "docker run",
                          "docker start", "docker rm", "hf download",
                          "snapshot_download(", "shell=True",
                          "model-00001.safetensors"):
            self.assertNotIn(forbidden, s)
        self.assertIn("ROOT_URL", s)
        self.assertIn("MAX_PAGE_BYTES", s)


if __name__ == "__main__":
    unittest.main()
