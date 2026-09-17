from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ServiceDeploymentTests(unittest.TestCase):
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

    def test_service_runner_strictly_parses_install_manifest(self) -> None:
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")
        self.assertIn('parse_state_into_vars install-runtime "${STATE_FILE}"', runner)
        self.assertIn("installation manifest failed strict runtime parsing", runner)
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

    def test_service_readiness_requires_runtime_commit_attestation(self) -> None:
        manager = (ROOT / "scripts" / "manage-service.sh").read_text(encoding="utf-8")
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")
        self.assertIn("runtime-commit.env", manager)
        self.assertIn("runtime-commit.env", runner)
        self.assertIn('runtime_commit_matches "${candidate_container_id}"', manager)
        self.assertIn('curl -fsS --max-time 3 http://127.0.0.1:8888/health', manager)
        self.assertIn('bash "${RUNTIME_TRANSITION}" commit', runner)
        self.assertIn('write_runtime_commit_attestation "${container_id}"', runner)
        self.assertLess(runner.index('bash "${RUNTIME_TRANSITION}" commit'), runner.index('write_runtime_commit_attestation "${container_id}"'))
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
        self.assertIn('docker top "${CONTAINER_NAME}" -eo comm', manager)
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
        self.assertLess(runner.index('log_runtime_phase "transition-committed"'), runner.index('log_runtime_phase "runtime-attestation-written"'))

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

    def test_doctor_checks_runtime_lifecycle_drift(self) -> None:
        doctor = (ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
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
