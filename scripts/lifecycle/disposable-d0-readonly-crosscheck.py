#!/usr/bin/env python3
"""Read-only, on-host D0 cross-check for a separately provisioned disposable host.

NEVER authorizes D0 admission, D1-D5, service operations, or GPU/model runs.
Refuses to probe until supplied policy/inventory passes offline checks and an
explicit independent-host acknowledgement is provided. No files are written.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
D0_PARSER = Path(__file__).with_name("disposable-d0-preflight.py")
MAX_OUTPUT = 8192
MAX_MOUNTINFO = 1024 * 1024
DOCKER_ENDPOINT_FORMAT = '{{ (index .Endpoints "docker").Host }}'
DOCKER_OVERRIDE_KEYS = (
    "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY",
    "DOCKER_CERT_PATH", "DOCKER_CONFIG", "DOCKER_API_VERSION",
)
DEFAULT_DOCKER_SOCKETS = frozenset(("/var/run/docker.sock", "/run/docker.sock"))


class Refusal(Exception):
    """Sanitized refusal; never include machine-specific text."""


def require(value: bool, code: str) -> None:
    if not value:
        raise Refusal(code)


def load_policy_module() -> Any:
    spec = importlib.util.spec_from_file_location("d0_offline", D0_PARSER)
    require(spec is not None and spec.loader is not None, "offline_parser_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReadonlyInspector:
    """Allow injected fixture readers, but production CLI has no override hooks."""

    def __init__(
        self,
        *,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        machine_file: Path = Path("/etc/machine-id"),
        mount_file: Path = Path("/proc/self/mountinfo"),
        path_is_dir: Callable[[str], bool] = os.path.isdir,
        path_real: Callable[[str], str] = os.path.realpath,
        socket_is_socket: Callable[[str], bool] | None = None,
        docker_env: Mapping[str, str] | None = None,
        host_env: Mapping[str, str] | None = None,
    ) -> None:
        self.socket_is_socket = socket_is_socket or (
            lambda path: stat.S_ISSOCK(os.stat(path).st_mode)
        )
        self.docker_env = dict(os.environ if docker_env is None else docker_env)
        self.host_env = dict(os.environ if host_env is None else host_env)
        self.run = run
        self.machine_file = machine_file
        self.mount_file = mount_file
        self.path_is_dir = path_is_dir
        self.path_real = path_real

    def command(self, *args: str) -> str:
        # Fixed, read-only argv only; no shell, sudo, network fetch or mutations.
        allowed = {
            ("git", "rev-parse", "HEAD"),
            ("git", "remote", "get-url", "origin"),
            ("git", "status", "--porcelain=v1", "--untracked-files=all"),
            ("docker", "context", "show"),
        }
        context_inspect = (
            len(args) == 6 and args[:3] == ("docker", "context", "inspect")
            and args[4:] == ("--format", DOCKER_ENDPOINT_FORMAT)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", args[3]) is not None
        )
        bound_info = (
            len(args) in (6, 7) and args[:2] == ("docker", "--context")
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", args[2]) is not None
            and args[3:] in (
                ("info", "--format", "{{.ID}}"),
                ("ps", "-a", "--format", "{{.ID}}"),
            )
        )
        service_show = (
            len(args) == 6 and args[:2] == ("systemctl", "show")
            and args[3:] == ("--property=LoadState", "--value", "--no-pager")
        )
        if args not in allowed and not (context_inspect or bound_info or service_show):
            raise Refusal("unsupported_host_probe")
        try:
            result = self.run(
                list(args), cwd=ROOT, text=True, capture_output=True,
                check=False, timeout=5,
                # 'git status' must not refresh/write the repository index.
                env={**self.host_env, "GIT_OPTIONAL_LOCKS": "0"},
            )
            if result.returncode != 0 or len(result.stdout) > MAX_OUTPUT:
                raise Refusal("read_only_probe_unavailable")
            return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired, UnicodeError):
            raise Refusal("read_only_probe_unavailable") from None

    def machine_hash(self) -> str:
        try:
            info = self.machine_file.lstat()
            import stat
            require(stat.S_ISREG(info.st_mode) and info.st_size <= 128, "machine_identity_unavailable")
            raw = self.machine_file.read_bytes()
            require(len(raw) <= 128, "machine_identity_unavailable")
            value = raw.decode("ascii").strip()
            require(bool(re.fullmatch(r"[0-9a-f]{32}", value)), "machine_identity_unavailable")
            return hashlib.sha256(value.encode("ascii")).hexdigest()
        except (OSError, UnicodeError):
            raise Refusal("machine_identity_unavailable") from None

    def mount_points(self) -> list[str]:
        try:
            import stat
            info = self.mount_file.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_MOUNTINFO, "mount_inventory_unavailable")
            data = self.mount_file.read_bytes()
            require(len(data) <= MAX_MOUNTINFO, "mount_inventory_unavailable")
            points: list[str] = []
            for line in data.decode("utf-8").splitlines():
                fields = line.split(" - ", 1)[0].split()
                require(len(fields) >= 5, "mount_inventory_invalid")
                raw = fields[4]
                point = re.sub(
                    r"\\([0-7]{3})",
                    lambda m: chr(int(m.group(1), 8)),
                    raw,
                )
                require(point.startswith("/") and "\x00" not in point, "mount_inventory_invalid")
                points.append(point)
            require(bool(points), "mount_inventory_unavailable")
            return points
        except (OSError, UnicodeError):
            raise Refusal("mount_inventory_unavailable") from None

    def check(self, policy: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
        # Git environment and system bus selectors can re-target even read-only
        # commands. Refuse before any Git/Docker/systemd probe; the only
        # accepted Git setting is the explicitly enforced no-optional-locks flag.
        require(
            not any(
                value and (
                    (key.startswith("GIT_") and not (
                        key == "GIT_OPTIONAL_LOCKS" and value == "0"
                    ))
                    or key.startswith("SYSTEMD_")
                    or key in ("DBUS_SYSTEM_BUS_ADDRESS", "DBUS_SESSION_BUS_ADDRESS")
                )
                for key, value in self.host_env.items()
            ),
            "untrusted_git_or_systemd_environment",
        )
        # Verify protected machine ID before contacting Docker/systemd.
        machine = self.machine_hash()
        require(machine not in policy["protected_machine_id_hashes"], "protected_machine_identity")
        require(machine == inventory["host"]["machine_id_sha256"], "machine_identity_mismatch")

        observed_sha = self.command("git", "rev-parse", "HEAD")
        require(observed_sha == policy["expected_sha"] == inventory["git"]["sha"], "git_head_mismatch")
        observed_origin = self.command("git", "remote", "get-url", "origin")
        require(observed_origin == inventory["git"]["origin"], "git_origin_mismatch")
        require(
            self.command("git", "status", "--porcelain=v1", "--untracked-files=all") == "",
            "git_worktree_not_clean",
        )

        points = self.mount_points()
        roots = [inventory["paths"][k] for k in ("work_root", "model_root", "log_root")]
        for root in roots:
            require(self.path_is_dir(root), "disposable_root_missing")
            require(self.path_real(root) == root, "disposable_root_realpath_drift")
            require(
                not any(
                    point != "/" and (
                        point == root
                        or point.startswith(root + "/")
                        or root.startswith(point.rstrip("/") + "/")
                    )
                    for point in points
                ),
                "mount_overlapping_disposable_root",
            )

        require(
            not any(
                value for key, value in self.docker_env.items()
                if key.startswith("DOCKER_")
            ),
            "docker_environment_override",
        )
        context = self.command("docker", "context", "show")
        require(context == inventory["docker"]["context"], "docker_context_mismatch")
        require(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", context) is not None,
            "unsupported_docker_context_name",
        )
        endpoint = self.command(
            "docker", "context", "inspect", context,
            "--format", DOCKER_ENDPOINT_FORMAT,
        )
        require(endpoint.startswith("unix:///"), "remote_or_unknown_docker_endpoint")
        socket_path = endpoint.removeprefix("unix://")
        require(
            socket_path not in DEFAULT_DOCKER_SOCKETS
            and os.path.normpath(socket_path) == socket_path
            and self.path_real(socket_path) == socket_path,
            "shared_or_aliased_docker_socket",
        )
        require(
            not any(
                os.path.commonpath((socket_path, root)) == root
                for root in policy["forbidden_roots"]
            ),
            "docker_socket_in_protected_root",
        )
        require(
            not any(
                point != "/" and (
                    point == socket_path
                    or socket_path.startswith(point.rstrip("/") + "/")
                )
                for point in points
            ),
            "docker_socket_mount_overlap",
        )
        try:
            require(self.socket_is_socket(socket_path), "docker_socket_unavailable")
        except OSError:
            raise Refusal("docker_socket_unavailable") from None
        daemon = self.command("docker", "--context", context, "info", "--format", "{{.ID}}")
        require(bool(daemon), "docker_daemon_unknown")
        require(daemon not in policy["protected_docker_daemon_ids"], "protected_docker_daemon")
        require(daemon == inventory["docker"]["daemon_id"], "docker_daemon_mismatch")
        require(
            self.command("docker", "--context", context, "ps", "-a", "--format", "{{.ID}}") == "",
            "docker_has_existing_containers",
        )

        unit = inventory["service"]["unit"]
        require(
            self.command(
                "systemctl", "show", unit,
                "--property=LoadState", "--value", "--no-pager",
            ) == "not-found",
            "service_unit_already_present_or_unknown",
        )

        # No positive trust claim about operator ownership, Docker isolation,
        # external users, snapshot recovery, or mounts outside these three roots.
        return {
            "schema_version": 1,
            "scope": "ON_HOST_READ_ONLY_ASSERTION_CROSSCHECK",
            "git_sha": observed_sha,
            "host_identity": "MATCHED_SUPPLIED_INVENTORY_NOT_ATTESTED",
            "docker_daemon": "MATCHED_SUPPLIED_INVENTORY_NOT_ATTESTED",
            "docker_containers": "NONE_REPORTED",
            "configured_service_unit": "NOT_FOUND",
            "candidate_root_mounts": "NONE_DETECTED_IN_SELECTED_ROOTS",
            "independence": "NOT_ATTESTED",
            "d0_admission": "NOT_GRANTED",
            "d1_d5": "NOT_AUTHORIZED",
            "live_host_e2e": "NOT_QUALIFIED",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument(
        "--ack-independent-disposable-host", action="store_true",
        help="Acknowledge that the target is a separately approved throwaway machine; not the protected DGX",
    )
    args = parser.parse_args(argv)
    try:
        require(args.ack_independent_disposable_host, "independent_host_ack_required")
        offline = load_policy_module()
        policy = offline.read_json(args.policy)
        inventory = offline.read_json(args.inventory)
        offline.validate(policy, inventory)
        result = ReadonlyInspector().check(policy, inventory)
    except Refusal as exc:
        print("D0_READONLY_CROSSCHECK=REFUSED")
        print("D0_REASON=" + str(exc))
        print("D0_ADMISSION=NOT_GRANTED")
        return 2
    except Exception as exc:
        # Offline parser has a stable refusal exception. Never leak raw input,
        # host identifiers or exception messages.
        if type(exc).__name__ == "PreflightRefusal":
            print("D0_READONLY_CROSSCHECK=REFUSED")
            print("D0_REASON=offline_policy_rejected")
            print("D0_ADMISSION=NOT_GRANTED")
            return 2
        print("D0_READONLY_CROSSCHECK=REFUSED")
        print("D0_REASON=unavailable_or_invalid_host_probe")
        print("D0_ADMISSION=NOT_GRANTED")
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
