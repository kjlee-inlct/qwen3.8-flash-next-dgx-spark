"""Synthetic offline safety tests: one-time approved CPU-only peer C CLI probe."""
from __future__ import annotations

from contextlib import redirect_stdout
import base64
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/runtime/orcarouter-peer-c-cli-probe.py"
SPEC = importlib.util.spec_from_file_location("peer_c_cli_probe", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class PeerCCliProbeTest(unittest.TestCase):
    def test_plan_never_calls_docker_or_host(self):
        with mock.patch.object(MOD, "query", side_effect=AssertionError("host")), \
             mock.patch.object(MOD, "preadmission", side_effect=AssertionError("host")), \
             mock.patch.object(MOD.subprocess, "run", side_effect=AssertionError("Docker")), \
             mock.patch("sys.argv", ["probe.py", "plan"]), \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(MOD.main(), 0)
        self.assertIn("PEER_C_SOURCE_ONLY_PLAN=PASS", out.getvalue())
        self.assertIn("NO_GPU_NO_NETWORK_NO_MOUNTS", out.getvalue())

    def test_run_refuses_without_explicit_approved_cpu_only(self):
        with mock.patch.object(MOD, "run_once", side_effect=AssertionError("run")), \
             mock.patch("sys.argv", ["probe.py", "run"]), \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(MOD.main(), 2)
        self.assertIn("BLOCKED_EXPLICIT_APPROVAL_FLAG", out.getvalue())

    def test_docker_arguments_are_mountless_offline_cpu_only_and_disposable(self):
        args = MOD.docker_args("qwen38-peer-c-cpu-cli-unique")
        self.assertEqual(args[:2], ["docker", "run"])
        self.assertIn("--pull=never", args)
        self.assertIn("--rm", args)
        self.assertEqual(args[args.index("--network") + 1], "none")
        self.assertEqual(args[args.index("--runtime") + 1], "runc")
        self.assertIn("--read-only", args)
        self.assertEqual(args[args.index("--cap-drop") + 1], "ALL")
        self.assertEqual(args[args.index("--user") + 1], "65534:65534")
        self.assertEqual(args[args.index("--memory") + 1], "4g")
        self.assertEqual(args[args.index("--memory-swap") + 1], "4g")
        self.assertIn("NVIDIA_VISIBLE_DEVICES=void", args)
        self.assertIn("CUDA_VISIBLE_DEVICES=-1", args)
        self.assertIn("HF_HUB_OFFLINE=1", args)
        self.assertIn("VLLM_NO_USAGE_STATS=1", args)
        self.assertEqual(args[args.index("--entrypoint") + 1], "python3")
        self.assertEqual(args[args.index(MOD.PEER.PINNED) + 1], "-c")
        self.assertEqual(args[-1], MOD.IN_CONTAINER)
        for forbidden in ("--gpus", "--device", "--mount", "-v", "-p",
                          "--privileged", "--ipc=host", "--network=host",
                          "--pull=always", "--restart", "--publish"):
            self.assertNotIn(forbidden, args)
        self.assertIn('["vllm", "serve", "--help=all"]', MOD.IN_CONTAINER)
        self.assertNotIn('["vllm", "serve", "/model"]', MOD.IN_CONTAINER)

    def test_single_successful_cpu_probe_is_audited_and_cannot_repeat(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            approval = root / "approved-once.json"
            name_observed = []
            rawhelp = b"example --kv-cache-memory-bytes 0  --speculative-config"
            stdout = "\n".join((
                "PEER_C_CONTAINER_OPERATION=CLI_HELP_AND_DIST_METADATA_ONLY",
                "PEER_C_PACKAGE_VLLM=0.29-dev",
                "PEER_C_FLAG_KV_CACHE_MEMORY_BYTES=PRESENT_IN_HELP",
                "PEER_C_HELP_BASE64=" + base64.b64encode(rawhelp).decode(),
                "PEER_C_CLI_HELP=PASS_METADATA_ONLY_NO_MODEL",
            ))
            before = {"qwen38-flash-next": {
                "id": "a" * 64, "image": "sha256:" + "b" * 64,
                "status": "exited", "running": False, "oom_killed": False,
            }}
            def fake_query(*args):
                self.assertEqual(args[:3], ("docker", "container", "inspect"))
                return subprocess.CompletedProcess(args, 1, "", "no such container")
            def fake_run(args, **kwargs):
                self.assertEqual(args[:2], ["docker", "run"])
                self.assertNotIn("--gpus", args)
                name_observed.append(args[args.index("--name") + 1])
                return subprocess.CompletedProcess(args, 0, stdout, "")
            with mock.patch.object(MOD, "OUTROOT", root), \
                 mock.patch.object(MOD, "ONCE", approval), \
                 mock.patch.object(MOD, "preadmission",
                                   return_value=("a" * 40, before)), \
                 mock.patch.object(MOD, "query", side_effect=fake_query), \
                 mock.patch.object(MOD, "receipt", return_value=before), \
                 mock.patch.object(MOD.PEER, "protected_receipt",
                                   return_value="THREE_STOPPED_EXISTING_IDS"), \
                 mock.patch.object(MOD.PEER, "metadata", return_value=None), \
                 mock.patch.object(MOD.subprocess, "run", side_effect=fake_run), \
                 redirect_stdout(io.StringIO()) as out:
                self.assertEqual(MOD.run_once(), 0)
                self.assertEqual(len(name_observed), 1)
                self.assertTrue(approval.is_file())
                self.assertIn("PEER_C_CLI_PROBE=PASS_METADATA_ONLY",
                              out.getvalue())
                self.assertIn("PEER_C_PROTECTED_AFTER=UNCHANGED",
                              out.getvalue())
                self.assertIn("PEER_C_DISPOSABLE_PROBE_REMOVED=YES",
                              out.getvalue())
                folders = [path for path in root.glob("peer-c-cli-*")
                           if path.is_dir()]
                self.assertEqual(len(folders), 1)
                self.assertEqual((folders[0] / "vllm-serve-help-all.txt").read_bytes(),
                                 rawhelp)
                self.assertTrue((folders[0] / "SHA256SUMS.txt").is_file())
                with self.assertRaisesRegex(MOD.ProbeError, "already consumed"):
                    MOD.run_once()
                self.assertEqual(len(name_observed), 1)

    def test_probe_docker_failure_does_not_claim_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            def fake_query(*args):
                return subprocess.CompletedProcess(args, 1, "", "not found")
            def fake_run(args, **kwargs):
                return subprocess.CompletedProcess(args, 1, "", "unable to run runc")
            with mock.patch.object(MOD, "OUTROOT", root), \
                 mock.patch.object(MOD, "ONCE", root / "once.json"), \
                 mock.patch.object(MOD, "preadmission",
                                   return_value=("b" * 40, {})), \
                 mock.patch.object(MOD, "query", side_effect=fake_query), \
                 mock.patch.object(MOD, "receipt", return_value={}), \
                 mock.patch.object(MOD.PEER, "protected_receipt",
                                   return_value="THREE_STOPPED_EXISTING_IDS"), \
                 mock.patch.object(MOD.PEER, "metadata", return_value=None), \
                 mock.patch.object(MOD.subprocess, "run", side_effect=fake_run), \
                 redirect_stdout(io.StringIO()) as out:
                self.assertEqual(MOD.run_once(), 2)
            self.assertIn("PEER_C_CLI_PROBE=FAILED_REVIEW", out.getvalue())

    def test_guard_rejects_wrong_image_and_never_checks_host(self):
        good = subprocess.CompletedProcess(None, 0, "feature/wizard-modular-phase1-20261014\n", "")
        clean = subprocess.CompletedProcess(None, 0, "", "")
        sha = subprocess.CompletedProcess(None, 0, "a" * 40 + "\n", "")
        with mock.patch.object(MOD, "query", side_effect=[good, clean, sha]), \
             mock.patch.object(MOD.PEER, "image_receipt",
                               return_value="IMAGE_CONFIG_ID_MISMATCH"), \
             mock.patch.object(MOD.PEER, "host_check",
                               side_effect=AssertionError("host")), \
             self.assertRaisesRegex(MOD.ProbeError, "image/config ID"):
            MOD.preadmission()

    def test_failed_help_is_classified_as_not_evaluated(self):
        self.assertIn('"NOT_EVALUATED_HELP_FAILED" if p.returncode != 0',
                      MOD.IN_CONTAINER)
        self.assertIn('"PRESENT_IN_HELP" if re.search(pattern, combined)',
                      MOD.IN_CONTAINER)

    def test_report_reads_consumed_failed_probe_without_new_docker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "peer-c-cli-20261018T115111Z-5e41d75a"
            out.mkdir()
            (root / "peer-c-cli-approved-once-20261018.json").write_text(
                json.dumps({
                    "operation": "one-time-cpu-cli-probe",
                    "approved_scope": "NO_GPU_NO_MODEL_NO_NETWORK",
                    "source_sha": "4873016f1d9fd864e6cce30c18fb96634b412fe3",
                    "name": "qwen38-peer-c-cpu-cli-20261018T115111Z-5e41d75a",
                    "evidence": str(out),
                }),
                encoding="utf-8")
            (out / "vllm-serve-help-all.txt").write_text(
                "Traceback (most recent call last):\n"
                '  File "/usr/local/lib/python3.12/dist-packages/vllm/config/device.py", line 56\n'
                "    default = default.default_factory()\n"
                "RuntimeError: Failed to infer device type\n",
                encoding="utf-8")
            (out / "raw.log").write_text(
                "PEER_C_PACKAGE_VLLM=0.1.dev20073+g8e685d198\n"
                "PEER_C_HELP_EXIT_CODE=1\nPEER_C_CLI_HELP=FAILED\n"
                "PEER_C_HELP_BASE64=THIS_IS_NOT_PRINTED\n",
                encoding="utf-8")
            record = {"qwen38-flash-next": {"id": "a" * 64}}
            (out / "before-protected.json").write_text(json.dumps(record))
            (out / "after-protected.json").write_text(json.dumps(record))
            with mock.patch.object(MOD, "OUTROOT", root), \
                 mock.patch.object(MOD, "ONCE",
                                   root / "peer-c-cli-approved-once-20261018.json"), \
                 mock.patch.object(MOD, "query", side_effect=AssertionError("Docker")), \
                 mock.patch.object(MOD.subprocess, "run",
                                   side_effect=AssertionError("subprocess")), \
                 mock.patch("sys.argv", ["probe.py", "report"]), \
                 redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(MOD.main(), 0)
            text = stdout.getvalue()
            self.assertIn("PEER_C_CLI_FLAGS=NOT_EVALUATED_HELP_FAILED", text)
            self.assertIn("PEER_C_SAVED_PROTECTED=UNCHANGED", text)
            self.assertIn("RuntimeError: Failed to infer device type", text)
            self.assertIn(
                "PEER_C_SAVED_FAILURE_CLASS=DEVICE_INFERENCE_FAILED_IN_GPU_HIDDEN_PROBE",
                text)
            self.assertIn("PEER_C_GPU_RUNTIME=NOT_TESTED_BY_CPU_ONLY_PROBE", text)
            self.assertIn("PEER_C_BACKEND_WIZARD_INSTALL_SWITCH=NOT_QUALIFIED",
                          text)
            self.assertNotIn("THIS_IS_NOT_PRINTED", text)
            self.assertIn("PEER_C_SAVED_REPORT=READ_ONLY_COMPLETE_NO_REPEAT", text)

    def test_saved_help_failure_unknown_is_not_misattributed_to_gpu(self):
        raw = "PEER_C_HELP_EXIT_CODE=1\nPEER_C_CLI_HELP=FAILED\n"
        text = "Traceback:\nImportError: unrelated missing module"
        self.assertEqual(
            MOD.classify_saved_help_error(text, raw),
            "HELP_FAILED_CAUSE_UNDETERMINED")

    def test_saved_help_success_is_never_called_device_failure(self):
        raw = "PEER_C_HELP_EXIT_CODE=0\nPEER_C_CLI_HELP=PASS_METADATA_ONLY_NO_MODEL\n"
        text = ("vllm/config/device.py\nRuntimeError: Failed to infer device type"
                "\ndefault.default_factory()")
        self.assertEqual(
            MOD.classify_saved_help_error(text, raw),
            "NOT_A_RECORDED_HELP_FAILURE")

    def test_missing_traceback_frames_is_unknown_not_proof(self):
        raw = "PEER_C_CLI_HELP=FAILED\n"
        self.assertEqual(
            MOD.classify_saved_help_error(
                "RuntimeError: Failed to infer device type", raw),
            "HELP_FAILED_CAUSE_UNDETERMINED")

    def test_report_no_receipt_blocks_without_spawning_docker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(MOD, "OUTROOT", root), \
                 mock.patch.object(MOD, "ONCE", root / "missing.json"), \
                 mock.patch.object(MOD.subprocess, "run",
                                   side_effect=AssertionError("Docker")), \
                 mock.patch("sys.argv", ["probe.py", "report"]), \
                 redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(MOD.main(), 2)
            self.assertIn("PEER_C_SAVED_REPORT=NO_APPROVED_RECEIPT",
                          stdout.getvalue())

    def test_report_rejects_external_evidence_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "peer-c-cli-approved-once-20261018.json").write_text(
                json.dumps({
                    "operation": "one-time-cpu-cli-probe",
                    "approved_scope": "NO_GPU_NO_MODEL_NO_NETWORK",
                    "source_sha": "a" * 40,
                    "name": "qwen38-peer-c-cpu-cli-foo",
                    "evidence": "/tmp/unrelated/peer-c-cli-foo",
                }))
            with mock.patch.object(MOD, "OUTROOT", root), \
                 mock.patch.object(MOD, "ONCE",
                                   root / "peer-c-cli-approved-once-20261018.json"), \
                 mock.patch.object(MOD.subprocess, "run",
                                   side_effect=AssertionError("Docker")), \
                 mock.patch("sys.argv", ["probe.py", "report"]), \
                 redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(MOD.main(), 2)
            self.assertIn("PEER_C_SAVED_REPORT=BLOCKED_READ_ERROR",
                          stdout.getvalue())

    def test_timeout_stop_rejects_unowned_or_protected_containers(self):
        protected_id = MOD.PEER.PROTECTED_IDENTITIES["qwen38-flash-next"][0]
        obj = {
            "Id": protected_id, "Image": MOD.PEER.EXPECTED_IMAGE_ID,
            "Config": {"Labels": {"qwen38.peer-c-cpu-cli-probe": "20261018"}},
        }
        with mock.patch.object(MOD.PEER, "metadata", return_value=obj), \
             mock.patch.object(MOD.subprocess, "run",
                               side_effect=AssertionError("stopping old Docker")):
            with self.assertRaisesRegex(MOD.ProbeError, "invalid/protected"):
                MOD.recover_own_timeout("probe-new")
        obj["Id"] = "c" * 64
        obj["Config"]["Labels"] = {"qwen38.peer-c-cpu-cli-probe": "untrusted"}
        with mock.patch.object(MOD.PEER, "metadata", return_value=obj), \
             mock.patch.object(MOD.subprocess, "run",
                               side_effect=AssertionError("unowned stop")):
            with self.assertRaisesRegex(MOD.ProbeError, "ownership mismatch"):
                MOD.recover_own_timeout("probe-new")


if __name__ == "__main__":
    unittest.main()
