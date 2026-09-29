from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
TOOL = ROOT / "scripts" / "lib" / "asset_ownership.py"
STATE_PARSER = ROOT / "scripts" / "lib" / "state_file.py"


class AssetOwnershipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.registry = self.base / "state" / "asset-ownership.json"
        self.model_root = self.base / "models"
        self.model_root.mkdir(parents=True)
        self.bin_dir = self.base / "bin"
        self.bin_dir.mkdir()
        docker = self.bin_dir / "docker"
        docker.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == image && "${2:-}" == inspect ]]; then
  if [[ -z "${FAKE_IMAGE_ID:-}" ]]; then
    exit 1
  fi
  printf '%s\\n' "${FAKE_IMAGE_ID}"
  exit 0
fi
if [[ "${1:-}" == ps ]]; then
  exit 0
fi
exit 1
""",
            encoding="utf-8",
        )
        docker.chmod(docker.stat().st_mode | stat.S_IXUSR)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def env(self, image_id: str = "") -> dict[str, str]:
        return {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ.get('PATH', '')}",
            "FAKE_IMAGE_ID": image_id,
        }

    def run_tool(
        self, *args: str, image_id: str = ""
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(TOOL), *args],
            cwd=ROOT,
            env=self.env(image_id),
            text=True,
            capture_output=True,
            check=False,
        )

    def managed_model(self, name: str, *, hybrid: bool = False) -> Path:
        path = self.model_root / name
        path.mkdir()
        marker = (
            path / ".qwen38-hybrid-manifest.json"
            if hybrid
            else path / ".qwen38-model-manifest.json"
        )
        marker.write_text(
            json.dumps(
                {
                    "status": "complete",
                    "variant": name if hybrid else None,
                    "repository": "example/model",
                    "revision": "a" * 40,
                }
            ),
            encoding="utf-8",
        )
        return path

    def track_model(
        self, path: Path, *, owned: bool, dependencies: tuple[Path, ...] = ()
    ) -> subprocess.CompletedProcess[str]:
        args = [
            "track-model",
            str(self.registry),
            str(path),
            str(self.model_root),
            "--owned",
            "1" if owned else "0",
        ]
        for dependency in dependencies:
            args.extend(["--depends", str(dependency)])
        return self.run_tool(*args)

    def test_registry_preserves_multiple_profile_models(self) -> None:
        orca = self.managed_model("qwen3.8-flash-next-orcarouter")
        nvidia = self.managed_model("qwen3.8-flash-next-nvidia")

        self.assertEqual(self.track_model(orca, owned=True).returncode, 0)
        self.assertEqual(self.track_model(nvidia, owned=True).returncode, 0)

        for path in (orca, nvidia):
            result = self.run_tool("owns-model", str(self.registry), str(path))
            self.assertEqual(result.returncode, 0, result.stderr)

        plan = self.run_tool("plan-purge", str(self.registry), "--kind", "model")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertIn(str(orca.resolve()), plan.stdout)
        self.assertIn(str(nvidia.resolve()), plan.stdout)

    def test_hybrid_purge_order_removes_dependents_first(self) -> None:
        base = self.managed_model("base")
        h3 = self.managed_model("h3", hybrid=True)
        h4 = self.managed_model("h4", hybrid=True)
        h5 = self.managed_model("h5", hybrid=True)
        h6 = self.managed_model("h6", hybrid=True)

        entries = (
            (base, ()),
            (h3, (base,)),
            (h4, (base, h3)),
            (h5, (base, h3, h4)),
            (h6, (base, h3, h4, h5)),
        )
        for path, dependencies in entries:
            result = self.track_model(path, owned=True, dependencies=dependencies)
            self.assertEqual(result.returncode, 0, result.stderr)

        plan = self.run_tool("plan-purge", str(self.registry), "--kind", "model")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        paths = [line.split("\t", 1)[1] for line in plan.stdout.splitlines()]
        self.assertLess(paths.index(str(h6.resolve())), paths.index(str(h5.resolve())))
        self.assertLess(paths.index(str(h5.resolve())), paths.index(str(h4.resolve())))
        self.assertLess(paths.index(str(h4.resolve())), paths.index(str(h3.resolve())))
        self.assertLess(paths.index(str(h3.resolve())), paths.index(str(base.resolve())))

    def test_unowned_dependent_blocks_owned_dependency_purge(self) -> None:
        base = self.managed_model("base")
        h3 = self.managed_model("h3", hybrid=True)
        self.assertEqual(self.track_model(base, owned=True).returncode, 0)
        self.assertEqual(
            self.track_model(h3, owned=False, dependencies=(base,)).returncode, 0
        )

        result = self.run_tool(
            "preflight-purge", str(self.registry), "--kind", "model"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required by a retained dependent", result.stderr)
        self.assertIn(str(h3.resolve()), result.stderr)

    def test_owned_model_manifest_drift_fails_closed(self) -> None:
        model = self.managed_model("orcarouter")
        self.assertEqual(self.track_model(model, owned=True).returncode, 0)
        marker = model / ".qwen38-model-manifest.json"
        marker.write_text('{"status":"complete","changed":true}\n', encoding="utf-8")

        result = self.run_tool(
            "preflight-one", str(self.registry), "model", str(model)
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest drift", result.stderr)

    def test_owned_image_id_drift_fails_closed(self) -> None:
        first = "sha256:" + "a" * 64
        second = "sha256:" + "b" * 64
        tracked = self.run_tool(
            "track-image",
            str(self.registry),
            "vllm-test:v1",
            "--owned",
            "1",
            image_id=first,
        )
        self.assertEqual(tracked.returncode, 0, tracked.stderr)

        result = self.run_tool(
            "preflight-one",
            str(self.registry),
            "image",
            "vllm-test:v1",
            image_id=second,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("image ID drift", result.stderr)

    def test_bootstrap_imports_legacy_active_ownership_only(self) -> None:
        model = self.managed_model("legacy")
        state = self.base / "state" / "install.env"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(
            "\n".join(
                [
                    "SCHEMA_VERSION=4",
                    "PHASE=complete",
                    f"INSTALL_ROOT={ROOT}",
                    "MODEL_PROFILE=orcarouter",
                    "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                    f"MODEL_DIR={model}",
                    "MODEL_OWNED=1",
                    "SWAP_FILE=/swap-ple.img",
                    "SWAP_OWNED=0",
                    "VLLM_IMAGE=vllm-test:v1",
                    "IMAGE_OWNED=1",
                    "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "CONTAINER_NAME=qwen38-flash-next",
                    "CONFIG_OVERRIDE=",
                    "CONFIG_OWNED=0",
                    "MONITOR_PROTECT=0",
                    "MONITOR_ENABLED=0",
                    "MONITOR_MIN_AVAILABLE_GIB=6",
                    "MONITOR_MIN_FREE_GIB=2",
                    "MONITOR_FREE_GATE_GIB=10",
                    "MONITOR_MIN_SWAP_FREE_GIB=8",
                    "MONITOR_CONSECUTIVE=5",
                    "MONITOR_HEARTBEAT=60",
                    "API_ACCESS_MODE=local",
                    "API_DOCKER_PORT=8000",
                    "API_LAN_ADDRESS=",
                    "API_LAN_PORT=8001",
                    "PROXY_ENABLED=0",
                    "PROXY_OWNED=0",
                    "PROXY_PORT=8000",
                    "SERVICE_ENABLED=1",
                    "SERVICE_OWNED=0",
                    "SERVICE_UNIT=qwen38-flash-next.service",
                    "UI_LANG=en",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        image_id = "sha256:" + "c" * 64

        result = self.run_tool(
            "bootstrap-install",
            str(self.registry),
            str(state),
            str(STATE_PARSER),
            image_id=image_id,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.run_tool("owns-model", str(self.registry), str(model)).returncode, 0
        )
        self.assertEqual(
            self.run_tool(
                "owns-image", str(self.registry), "vllm-test:v1", image_id=image_id
            ).returncode,
            0,
        )


if __name__ == "__main__":
    unittest.main()
