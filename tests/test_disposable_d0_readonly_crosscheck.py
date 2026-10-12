"""Fixture-only D0 on-host read-only cross-check tests; no real host probing."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "lifecycle" / "disposable-d0-readonly-crosscheck.py"
PREVIOUS = ROOT / "scripts" / "lifecycle" / "disposable-d0-preflight.py"

def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

mod = load(SCRIPT, "d0_crosscheck")
fixtures = load(ROOT / "tests" / "test_disposable_d0_preflight.py", "d0_fixture_base")


class FakeHost:
    def __init__(self):
        self.events: list[tuple[str, ...]] = []
        self.probe_environments: list[dict[str, str]] = []
        self.answers = {
            ("git", "rev-parse", "HEAD"): "a" * 40,
            ("git", "remote", "get-url", "origin"): fixtures.base_inventory()["git"]["origin"],
            ("git", "status", "--porcelain=v1", "--untracked-files=all"): "",
            ("docker", "context", "show"): "isolated-fixture",
            ("docker", "context", "inspect", "isolated-fixture", "--format", mod.DOCKER_ENDPOINT_FORMAT):
                "unix:///srv/d0-docker/isolated.sock",
            ("docker", "--context", "isolated-fixture", "info", "--format", "{{.ID}}"):
                "disposable-daemon",
            ("docker", "--context", "isolated-fixture", "ps", "-a", "--format", "{{.ID}}"): "",
            (
                "systemctl", "show", "qwen38-d0-fixture.service",
                "--property=LoadState", "--value", "--no-pager",
            ): "not-found",
        }

    def run(self, args, **kwargs):
        self.events.append(tuple(args))
        self.probe_environments.append(kwargs.get("env", {}))
        if tuple(args) not in self.answers:
            raise OSError("simulated executable or daemon unavailable")
        return subprocess.CompletedProcess(args, 0, self.answers[tuple(args)], "")


class ReadonlyD0CrosscheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.host = FakeHost()
        self.machine = self.root / "machine-id"
        self.machine.write_text("a" * 32 + "\n", encoding="ascii")
        self.mounts = self.root / "mountinfo"
        self.mounts.write_text("1 0 8:1 / / rw - ext4 /dev/fake rw\n", encoding="utf-8")
        self.inventory = fixtures.base_inventory()
        self.inventory["host"]["machine_id_sha256"] = mod.hashlib.sha256(
            ("a" * 32).encode("ascii")
        ).hexdigest()
        self.policy = fixtures.base_policy()
        self.inspector = mod.ReadonlyInspector(
            run=self.host.run,
            machine_file=self.machine,
            mount_file=self.mounts,
            path_is_dir=lambda path: True,
            path_real=lambda path: path,
            socket_is_socket=lambda path: True,
            docker_env={},
        )

    def test_consistent_observations_never_authorize_d0(self):
        report = self.inspector.check(self.policy, self.inventory)
        self.assertEqual(report["d0_admission"], "NOT_GRANTED")
        self.assertEqual(report["d1_d5"], "NOT_AUTHORIZED")
        self.assertEqual(report["independence"], "NOT_ATTESTED")
        self.assertEqual(len(self.host.events), 8)
        self.assertIn(
            ("docker", "--context", "isolated-fixture", "info", "--format", "{{.ID}}"),
            self.host.events,
        )

    def test_git_optional_locks_disabled_for_all_readonly_probes(self):
        self.inspector.check(self.policy, self.inventory)
        self.assertTrue(self.host.probe_environments)
        self.assertTrue(all(
            e.get("GIT_OPTIONAL_LOCKS") == "0"
            for e in self.host.probe_environments
        ))

    def test_protected_machine_refuses_before_host_commands(self):
        self.policy["protected_machine_id_hashes"].append(
            self.inventory["host"]["machine_id_sha256"]
        )
        with self.assertRaisesRegex(mod.Refusal, "protected_machine_identity"):
            self.inspector.check(self.policy, self.inventory)
        self.assertEqual(self.host.events, [])

    def test_machine_identity_mismatch_refuses_before_docker(self):
        self.inventory["host"]["machine_id_sha256"] = "e" * 64
        with self.assertRaisesRegex(mod.Refusal, "machine_identity_mismatch"):
            self.inspector.check(self.policy, self.inventory)
        self.assertEqual(self.host.events, [])

    def test_git_drift_refuses_before_docker(self):
        self.host.answers[("git", "rev-parse", "HEAD")] = "f" * 40
        with self.assertRaisesRegex(mod.Refusal, "git_head_mismatch"):
            self.inspector.check(self.policy, self.inventory)
        self.assertEqual(self.host.events, [("git", "rev-parse", "HEAD")])

    def test_worktree_dirty_refuses_before_docker(self):
        self.host.answers[("git", "status", "--porcelain=v1", "--untracked-files=all")] = "?? untracked"
        with self.assertRaisesRegex(mod.Refusal, "git_worktree_not_clean"):
            self.inspector.check(self.policy, self.inventory)
        self.assertFalse(any(x[0] == "docker" for x in self.host.events))

    def test_symlinked_candidate_root_refuses_before_docker(self):
        self.inspector.path_real = lambda path: "/other" if path.endswith("d0-model") else path
        with self.assertRaisesRegex(mod.Refusal, "disposable_root_realpath_drift"):
            self.inspector.check(self.policy, self.inventory)
        self.assertFalse(any(x[0] == "docker" for x in self.host.events))

    def test_child_mount_refuses_before_docker(self):
        self.mounts.write_text(
            "1 0 8:1 / / rw - ext4 /dev/fake rw\n"
            "2 1 8:2 / /srv/d0-model/shared rw - ext4 /dev/foreign rw\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(mod.Refusal, "mount_overlapping_disposable_root"):
            self.inspector.check(self.policy, self.inventory)
        self.assertFalse(any(x[0] == "docker" for x in self.host.events))

    def test_parent_bind_mount_refuses_before_docker(self):
        self.mounts.write_text(
            "1 0 8:1 / / rw - ext4 /dev/fake rw\n"
            "2 1 8:2 / /srv rw - ext4 /dev/shared rw\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(mod.Refusal, "mount_overlapping_disposable_root"):
            self.inspector.check(self.policy, self.inventory)
        self.assertFalse(any(x[0] == "docker" for x in self.host.events))

    def test_docker_environment_override_refuses_before_docker(self):
        for key in mod.DOCKER_OVERRIDE_KEYS:
            with self.subTest(key=key):
                self.host.events.clear()
                self.inspector.docker_env = {key: "tcp://foreign:2375"}
                with self.assertRaisesRegex(mod.Refusal, "docker_environment_override"):
                    self.inspector.check(self.policy, self.inventory)
                self.assertFalse(any(x[0] == "docker" for x in self.host.events))

    def test_nonunix_or_default_socket_endpoint_refuses(self):
        key = ("docker", "context", "inspect", "isolated-fixture", "--format", mod.DOCKER_ENDPOINT_FORMAT)
        for endpoint, reason in (
            ("tcp://elsewhere:2375", "remote_or_unknown_docker_endpoint"),
            ("ssh://elsewhere", "remote_or_unknown_docker_endpoint"),
            ("unix:///var/run/docker.sock", "shared_or_aliased_docker_socket"),
            ("unix:///run/docker.sock", "shared_or_aliased_docker_socket"),
            ("unix:///srv/other/../d0-docker/isolated.sock", "shared_or_aliased_docker_socket"),
        ):
            with self.subTest(endpoint=endpoint):
                self.host.events.clear()
                self.host.answers[key] = endpoint
                with self.assertRaisesRegex(mod.Refusal, reason):
                    self.inspector.check(self.policy, self.inventory)
                self.assertFalse(any(x[:3] == ("docker", "--context", "isolated-fixture") for x in self.host.events))

    def test_socket_alias_or_missing_socket_refuses(self):
        key = ("docker", "context", "inspect", "isolated-fixture", "--format", mod.DOCKER_ENDPOINT_FORMAT)
        self.host.answers[key] = "unix:///srv/d0-docker/isolated.sock"
        self.inspector.path_real = lambda path: "/run/docker.sock" if path.endswith("isolated.sock") else path
        with self.assertRaisesRegex(mod.Refusal, "shared_or_aliased_docker_socket"):
            self.inspector.check(self.policy, self.inventory)
        self.inspector.path_real = lambda path: path
        self.inspector.socket_is_socket = lambda path: False
        with self.assertRaisesRegex(mod.Refusal, "docker_socket_unavailable"):
            self.inspector.check(self.policy, self.inventory)

    def test_protected_daemon_refuses_after_docker_info(self):
        self.policy["protected_docker_daemon_ids"].append("disposable-daemon")
        with self.assertRaisesRegex(mod.Refusal, "protected_docker_daemon"):
            self.inspector.check(self.policy, self.inventory)
        self.assertFalse(any(x[0] == "systemctl" for x in self.host.events))

    def test_existing_docker_container_refuses(self):
        self.host.answers[("docker", "--context", "isolated-fixture", "ps", "-a", "--format", "{{.ID}}")] = "abc"
        with self.assertRaisesRegex(mod.Refusal, "docker_has_existing_containers"):
            self.inspector.check(self.policy, self.inventory)

    def test_registered_service_refuses(self):
        key = ("systemctl", "show", "qwen38-d0-fixture.service", "--property=LoadState", "--value", "--no-pager")
        self.host.answers[key] = "loaded"
        with self.assertRaisesRegex(mod.Refusal, "service_unit_already_present_or_unknown"):
            self.inspector.check(self.policy, self.inventory)

    def test_docker_outage_fails_closed(self):
        self.host.answers.pop(("docker", "--context", "isolated-fixture", "info", "--format", "{{.ID}}"))
        with self.assertRaisesRegex(mod.Refusal, "read_only_probe_unavailable"):
            self.inspector.check(self.policy, self.inventory)

    def test_cli_requires_ack_before_probing_and_redacts_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy = Path(tmp) / "policy.json"
            inv = Path(tmp) / "inventory.json"
            policy.write_text(json.dumps(self.policy), encoding="utf-8")
            inv.write_text(json.dumps(self.inventory), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--policy", str(policy), "--inventory", str(inv)],
                capture_output=True, text=True, timeout=5, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("D0_REASON=independent_host_ack_required", result.stdout)
            self.assertNotIn(self.inventory["host"]["machine_id_sha256"], result.stdout)


if __name__ == "__main__":
    unittest.main()
