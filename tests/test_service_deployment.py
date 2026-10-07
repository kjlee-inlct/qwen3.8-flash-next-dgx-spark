from __future__ import annotations

import stat
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ServiceDeploymentTests(unittest.TestCase):
    def test_serve_helper_is_executable_for_immutable_release_cutover(self) -> None:
        serve = ROOT / "scripts" / "serve.sh"
        self.assertTrue(
            serve.stat().st_mode & stat.S_IXUSR,
            "scripts/serve.sh must keep its Git executable bit because immutable "
            "releases are produced with git archive and service-runner executes it directly",
        )

    def test_service_has_bounded_restart_and_loopback_runner(self) -> None:
        manager = (ROOT / "scripts" / "manage-service.sh").read_text(encoding="utf-8")
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")
        shim = (ROOT / "scripts" / "service-runner.sh").read_text(encoding="utf-8")
        self.assertIn("StartLimitBurst=2", manager)
        self.assertIn("Restart=on-failure", manager)
        self.assertIn("docker stop --timeout 30", manager)
        self.assertIn("WantedBy=multi-user.target", manager)
        self.assertNotIn('docker rm -f "${CONTAINER_NAME}"', manager)
        self.assertIn("--runtime-root", manager)
        self.assertIn("previous_container_id", manager)
        self.assertIn('"${candidate_container_id}" != "${previous_container_id}"', manager)
        self.assertIn("PUBLISH_HOST=127.0.0.1", runner)
        self.assertIn("RESTART_POLICY=no", runner)
        self.assertIn("pwd -P", runner)
        self.assertIn("docker wait", runner)
        self.assertIn("runtime/preflight-runtime.sh", runner)
        self.assertIn("runtime/runtime-transition.sh", runner)
        self.assertIn("runtime/service-runner.sh", shim)
        server = (ROOT / "scripts" / "serve.sh").read_text(encoding="utf-8")
        self.assertIn("--init", server)
        self.assertIn('if docker inspect "${NAME}"', server)
        self.assertIn("runtime container already exists", server)
        self.assertNotIn('docker rm -f "${NAME}"', server)

    def test_mazinb_managed_runtime_path_is_wired(self) -> None:
        server = (ROOT / "scripts" / "serve.sh").read_text(encoding="utf-8")
        runner = (
            ROOT / "scripts" / "runtime" / "service-runner.sh"
        ).read_text(encoding="utf-8")
        parser = (ROOT / "scripts" / "lib" / "state_file.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("mazinb)", server)
        self.assertIn("vllm-orcarouter-v029:v1", server)
        self.assertIn("VLLM_PLE_MMAP=1", server)
        self.assertIn("DEFAULT_QSA_EXACT_TOPK=1", server)
        self.assertIn("KV_MEMORY_FLAG=--kv-cache-memory-bytes", server)
        self.assertIn('"${MODEL_PROFILE:-}" == mazinb', runner)
        self.assertIn('one_of("orcarouter", "nvidia", "mazinb", "orcarouter-hybrid")', parser)

    def test_orcarouter_hybrid_managed_runtime_path_mounts_h6_parents(self) -> None:
        server = (ROOT / "scripts" / "serve.sh").read_text(encoding="utf-8")
        runner = (
            ROOT / "scripts" / "runtime" / "service-runner.sh"
        ).read_text(encoding="utf-8")
        preflight = (
            ROOT / "scripts" / "runtime" / "preflight-runtime.sh"
        ).read_text(encoding="utf-8")
        doctor = (ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
        start = server.index("  orcarouter-hybrid)\n")
        end = server.index("  *) echo", start)
        hybrid_block = server[start:end]
        self.assertIn("orcarouter-hybrid)", hybrid_block)
        self.assertIn("vllm-orcarouter-v029:v1", hybrid_block)
        self.assertIn("qwen3.8-h6-modelopt-w4a16", hybrid_block)
        for mount in ("/base-model:ro", "/h3-model:ro", "/h4-all:ro", "/h5-parent:ro"):
            self.assertIn(mount, hybrid_block)
        self.assertIn("PLE_MODE=mmap", hybrid_block)
        self.assertIn("DEFAULT_QSA_EXACT_TOPK=1", hybrid_block)
        self.assertNotIn("QWEN38_MARLIN_CANONICAL_SCOPE=decoder", hybrid_block)
        self.assertIn('"${MODEL_PROFILE:-}" == orcarouter-hybrid', runner)
        self.assertIn("validate-orcarouter-hybrid.py", preflight)
        self.assertIn("--runtime-only", preflight)
        self.assertIn("hybrid parent mount matches", doctor)
        self.assertIn("hybrid runtime uses PLE mmap", doctor)
        self.assertIn("hybrid runtime uses exact QSA", doctor)

    def test_service_runner_strictly_parses_install_manifest(self) -> None:
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")
        self.assertIn('parse_state_into_vars install-service-runtime "${STATE_FILE}"', runner)
        self.assertIn("installation manifest failed strict service-runtime parsing", runner)
        self.assertNotIn('source "${STATE_FILE}"', runner)
        self.assertNotIn("shellcheck disable=SC1090", runner)

    def test_service_manager_strictly_parses_install_manifest(self) -> None:
        manager = (ROOT / "scripts" / "manage-service.sh").read_text(encoding="utf-8")
        self.assertIn('install-service "${STATE_FILE}"', manager)
        self.assertIn("installation manifest failed strict service parsing", manager)
        self.assertIn("INSTALL_STATE_PARSER", manager)
        self.assertIn("RUNTIME_STATE_PARSER", manager)
        self.assertNotIn('source "${STATE_FILE}"', manager)
        self.assertNotIn("shellcheck disable=SC1090", manager)


    def test_service_manager_accepts_service_ready_phase(self) -> None:
        manager = (ROOT / "scripts" / "manage-service.sh").read_text(encoding="utf-8")
        self.assertIn('"${value}" == service_ready || "${value}" == complete', manager)

    def test_service_runner_recovers_profile_switch_before_manifest_parse(self) -> None:
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")

        self.assertIn("profile-switch-transition.sh", runner)
        self.assertIn('bash "${PROFILE_SWITCH_TRANSITION}" service-recover', runner)
        self.assertLess(
            runner.index('bash "${PROFILE_SWITCH_TRANSITION}" service-recover'),
            runner.index('parse_state_into_vars install-service-runtime "${STATE_FILE}"'),
        )

    def test_service_runner_uses_service_runtime_schema_for_initial_start(self) -> None:
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")
        self.assertIn('parse_state_into_vars install-service-runtime "${STATE_FILE}"', runner)
        self.assertNotIn('parse_state_into_vars install-runtime "${STATE_FILE}"', runner)

    def test_service_readiness_requires_runtime_commit_attestation(self) -> None:
        manager = (ROOT / "scripts" / "manage-service.sh").read_text(encoding="utf-8")
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")
        self.assertIn("runtime-commit.env", manager)
        self.assertIn("runtime-commit.env", runner)
        self.assertIn('runtime_commit_matches "${candidate_container_id}"', manager)
        self.assertIn('curl -fsS --max-time 3 http://127.0.0.1:8888/health', manager)
        self.assertIn('bash "${RUNTIME_TRANSITION}" commit', runner)
        self.assertIn('write_runtime_commit_attestation "${container_id}"', runner)
        self.assertIn("release_profile_refresh_owns_runtime_commit", runner)
        self.assertIn("transition-commit-deferred", runner)
        refresh_branch = runner.index('if [[ "${refresh_runtime_owner}" == 1 ]]')
        refresh_attest = runner.index('write_runtime_commit_attestation "${container_id}"', refresh_branch)
        standalone_commit = runner.index('bash "${RUNTIME_TRANSITION}" commit', refresh_branch)
        self.assertLess(refresh_attest, standalone_commit)
        self.assertIn("EXPECTED_RUNTIME_ROOT", manager)
        self.assertIn("ATTESTED_RUNTIME_ROOT", manager)
        self.assertIn("ATTESTED_CONTAINER_ID", manager)
        self.assertIn('rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"', manager)

    def test_service_readiness_reports_progress_details(self) -> None:
        manager = (ROOT / "scripts" / "manage-service.sh").read_text(encoding="utf-8")
        self.assertIn("print_readiness_progress()", manager)
        self.assertIn("service     :", manager)
        self.assertIn("container   :", manager)
        self.assertIn("health      :", manager)
        self.assertIn("attestation :", manager)
        self.assertIn("service log :", manager)
        self.assertIn("vLLM log    :", manager)
        self.assertIn("PLE worker  :", manager)
        self.assertIn('journalctl -u "${UNIT}" -n 1 --no-pager -o cat', manager)
        self.assertIn('docker logs --timestamps --tail 1 "${CONTAINER_NAME}"', manager)
        self.assertIn('docker top "${CONTAINER_NAME}" -eo pid,args', manager)
        self.assertIn('docker logs --tail 200 "${CONTAINER_NAME}"', manager)
        self.assertIn("seen-in-log", manager)
        self.assertIn("PleOffloadWorker", manager)
        self.assertIn('print_readiness_progress "$((attempt * 10))" "${candidate_container_id}"', manager)
        self.assertIn("1800 seconds", manager)

    def test_service_runner_reports_runtime_phase_timing(self) -> None:
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")
        self.assertIn('RUNTIME_PHASE_START_SECONDS="${SECONDS}"', runner)
        self.assertIn("log_runtime_phase()", runner)
        for phase in (
            "preflight-start",
            "preflight-complete",
            "transition-recovery-complete",
            "transition-prepared",
            "container-start-command-complete",
            "candidate-validating",
            "health-ready",
            "model-list-validated",
            "transition-committed",
            "runtime-attestation-written",
        ):
            self.assertIn(f'log_runtime_phase "{phase}"', runner)
        self.assertIn("elapsed=%ss", runner)
        self.assertLess(runner.index('log_runtime_phase "health-ready"'), runner.index('log_runtime_phase "model-list-validated"'))
        self.assertIn('log_runtime_phase "transition-commit-deferred"', runner)
        refresh_branch = runner.index('if [[ "${refresh_runtime_owner}" == 1 ]]')
        refresh_attest = runner.index('log_runtime_phase "runtime-attestation-written"', refresh_branch)
        deferred = runner.index('log_runtime_phase "transition-commit-deferred"', refresh_branch)
        self.assertLess(refresh_attest, deferred)
        standalone = runner.index("else", deferred)
        standalone_commit = runner.index('log_runtime_phase "transition-committed"', standalone)
        standalone_attest = runner.index('log_runtime_phase "runtime-attestation-written"', standalone_commit)
        self.assertLess(standalone_commit, standalone_attest)

    def test_release_qualification_does_not_mutate_payload(self) -> None:
        qualifier = (ROOT / "scripts" / "lifecycle" / "qualify-release.sh").read_text(encoding="utf-8")
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", qualifier)
        self.assertGreaterEqual(qualifier.count('bash "${RELEASE_MANAGER}" verify "${release_id}"'), 2)

    def test_memory_protection_stop_is_not_restarted_as_failure(self) -> None:
        monitor = (ROOT / "scripts" / "runtime" / "monitor-runtime.sh").read_text(encoding="utf-8")
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")
        self.assertIn("runtime-stop.env", monitor)
        self.assertIn("STOP_REASON=%q", monitor)
        self.assertIn("STOP_CONTAINER_NAME=%q", monitor)
        self.assertIn("STOP_CONTAINER_ID=%q", monitor)
        self.assertIn("runtime-stop.env", runner)
        self.assertIn("memory-protection", runner)
        self.assertIn('"${STOP_CONTAINER_ID:-}" == "${container_id}"', runner)
        self.assertIn("leaving service stopped", runner)
        self.assertIn("exit 0", runner)
        self.assertIn("stale runtime stop marker", runner)

    def test_memory_protection_during_startup_does_not_retry_candidate(self) -> None:
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")
        transition = (ROOT / "scripts" / "runtime" / "runtime-transition.sh").read_text(encoding="utf-8")
        self.assertIn("protected_stop_matches_container", runner)
        self.assertIn('bash "${RUNTIME_TRANSITION}" abort-protected', runner)
        self.assertIn("Candidate runtime was stopped by memory protection during startup", runner)
        self.assertIn("abort-protected)", transition)
        self.assertIn("left stopped after memory protection", transition)

    def test_doctor_checks_runtime_lifecycle_drift(self) -> None:
        doctor = (ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
        self.assertIn('realpath -m -- "${expected_hybrid_mounts[${destination}]}"', doctor)
        self.assertIn('actual_source_canonical', doctor)
        self.assertIn("runtime-transition.env", doctor)
        self.assertIn("no incomplete runtime transition exists", doctor)
        self.assertIn("no stale rollback container exists", doctor)
        self.assertIn("runtime container image matches installation manifest", doctor)
        self.assertIn("runtime model mount matches installation manifest", doctor)
        self.assertIn("runtime served model name matches installation manifest", doctor)
        self.assertIn("runtime image drift", doctor)
        self.assertIn("runtime model mount drift", doctor)
        self.assertIn("runtime served-name drift", doctor)

    def test_uninstaller_removes_only_owned_service(self) -> None:
        uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")
        self.assertIn('if [[ "${SERVICE_OWNED}" == 1 ]]', uninstaller)
        self.assertIn('manage-service.sh" remove --yes', uninstaller)


if __name__ == "__main__":
    unittest.main()
