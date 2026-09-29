from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ModelProfileTests(unittest.TestCase):
    def run_install(self, profile: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            return subprocess.run(
                [str(ROOT / "install.sh"), "--model", profile, "--lang", "en", "--yes", "--no-start", "--dry-run"],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )

    def run_wizard(self, choice: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            env = {**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")}
            env.pop("MODEL_PROFILE", None)
            answers = "\n".join(
                [
                    choice,  # model profile
                    "",      # default model directory
                    "n",     # no separate config override
                    "n",     # runtime memory monitor disabled
                    "1",     # local-only API
                    "y",     # install systemd service
                    "y",     # continue
                    "",
                ]
            )
            return subprocess.run(
                [str(ROOT / "install.sh"), "--lang", "en", "--no-start", "--dry-run"],
                cwd=ROOT,
                env=env,
                input=answers,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_model_registry_marks_orcarouter_as_only_stable_default(self) -> None:
        result = subprocess.run(
            [str(ROOT / "install.sh"), "--list-models"],
            cwd=ROOT,
            env=os.environ,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("orcarouter   stable", result.stdout)
        self.assertIn("nvidia       experimental", result.stdout)
        self.assertIn("mazinb       experimental", result.stdout)
        self.assertIn("orcarouter-hybrid experimental", result.stdout)
        self.assertIn("lychee888    planned", result.stdout)

    def test_mazinb_installable_profile_has_pinned_metadata(self) -> None:
        result = subprocess.run(
            [
                "bash",
                "-lc",
                'source scripts/model-profiles.sh; load_download_profile mazinb; '
                'printf "%s\n%s\n%s\n%s\n" "$PROFILE_REPO" "$PROFILE_REVISION" "$PROFILE_MODEL_DIR" "$PROFILE_SERVED_NAME"',
            ],
            cwd=ROOT,
            env=os.environ,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4", result.stdout)
        self.assertIn("f2c21eb", result.stdout)
        self.assertIn("qwen3.8-flash-next-mazinb", result.stdout)

    def test_candidate_download_requires_explicit_flag(self) -> None:
        help_result = subprocess.run(
            [str(ROOT / "scripts" / "download-weights.sh"), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--candidate", help_result.stdout)

    def test_planned_profiles_are_not_installable(self) -> None:
        result = self.run_install("lychee888")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is a planned profile and is not installable yet", result.stderr)

    def test_backend_registry_keeps_vllm_stable_and_sglang_planned(self) -> None:
        result = subprocess.run(
            [str(ROOT / "install.sh"), "--list-backends"],
            cwd=ROOT,
            env=os.environ,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("vllm", result.stdout)
        self.assertIn("stable", result.stdout)
        self.assertIn("sglang", result.stdout)
        self.assertIn("planned", result.stdout)


    def test_clean_host_wizard_can_select_every_installable_profile(self) -> None:
        expected = {
            "1": ("orcarouter", "qwen3.8-flash-next-orcarouter"),
            "2": ("nvidia", "qwen3.8-flash-next-nvidia"),
            "3": ("mazinb", "qwen3.8-flash-next-mazinb"),
            "4": ("orcarouter-hybrid", "qwen3.8-h6-modelopt-w4a16"),
        }
        for choice, (profile, model_dir) in expected.items():
            with self.subTest(profile=profile):
                result = self.run_wizard(choice)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"profile     : {profile}", result.stdout)
                self.assertIn(model_dir, result.stdout)
                self.assertIn("DRY-RUN complete", result.stdout)

    def test_wizard_labels_hybrid_composition_concisely(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertEqual(
            installer.count("OrcaRouter Hybrid H6 (OrcaRouter + mazinb experts, W4A16 NVFP4)"),
            2,
        )

    def test_clean_host_gated_profiles_do_not_require_hf_cli(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        downloader = (ROOT / "scripts" / "download-weights.sh").read_text(encoding="utf-8")

        self.assertIn("discover_hf_token()", installer)
        self.assertIn("ensure_profile_auth()", installer)
        self.assertIn("export HF_TOKEN", installer)
        self.assertIn("Hugging Face read token", installer)
        self.assertNotIn("command -v hf", installer)
        self.assertNotIn("hf auth whoami", installer)
        self.assertIn('TOKEN="${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-}}"', downloader)
        self.assertIn("curl -sS -L", downloader)

    def test_orcarouter_profile(self) -> None:
        result = self.run_install("orcarouter")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4", result.stdout)
        self.assertIn("profile     : orcarouter", result.stdout)
        self.assertIn("vllm-skinny-tp1:v1", result.stdout)

    def test_nvidia_profile(self) -> None:
        result = self.run_install("nvidia")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nvidia/Qwen3.8-Flash-Next-NVFP4", result.stdout)
        self.assertIn("fc694b54fb0174e0913e6adf86691ef85a4ead47", result.stdout)
        self.assertIn("profile     : nvidia", result.stdout)

    def test_mazinb_profile(self) -> None:
        result = self.run_install("mazinb")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4", result.stdout)
        self.assertIn("f2c21eb", result.stdout)
        self.assertIn("profile     : mazinb", result.stdout)
        self.assertIn("vllm-orcarouter-v029:v1", result.stdout)

    def test_orcarouter_hybrid_profile_is_generated_h6_checkpoint(self) -> None:
        result = self.run_install("orcarouter-hybrid")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("local/orcarouter-mazinb-h6-w4a16", result.stdout)
        self.assertIn("h6-modelopt-w4a16-v1", result.stdout)
        self.assertIn("qwen3.8-h6-modelopt-w4a16", result.stdout)
        self.assertIn("profile     : orcarouter-hybrid", result.stdout)
        self.assertIn("vllm-orcarouter-v029:v1", result.stdout)
        self.assertIn("hybrid base", result.stdout)
        self.assertIn("hybrid mix", result.stdout)

    def test_orcarouter_hybrid_registry_marks_local_build_sources(self) -> None:
        result = subprocess.run(
            [
                "bash",
                "-lc",
                'source scripts/model-profiles.sh; load_model_profile orcarouter-hybrid; '
                'printf "%s\\n%s\\n%s\\n%s\\n%s\\n" "$PROFILE_LOCAL_BUILD" '
                '"$PROFILE_BASE_PROFILE" "$PROFILE_OVERLAY_PROFILE" "$PROFILE_MODEL_DIR" "$PROFILE_IMAGE"',
            ],
            cwd=ROOT,
            env=os.environ,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines()[:3],
            ["1", "orcarouter", "mazinb"],
        )
        self.assertIn("qwen3.8-h6-modelopt-w4a16", result.stdout)
        self.assertIn("vllm-orcarouter-v029:v1", result.stdout)

    def test_h3_reuse_requires_pinned_source_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            h3 = Path(directory) / "h3"
            h3.mkdir()
            (h3 / "model.safetensors.index.json").write_text("{}", encoding="utf-8")
            manifest = {
                "status": "complete",
                "variant": "quant-layout-mazinb-experts",
                "base_revision": "c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                "overlay_revision": "f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f",
                "group0_bf16_weights": 300,
                "group0_fp8_scales_removed": 300,
                "base_expert_tensors_removed": 221184,
                "overlay_expert_tensors_added": 294912,
                "quantization_config_source": "mazinb-modelopt-nvfp4",
                "mtp_tensors_changed": 0,
            }
            manifest_path = h3 / ".qwen38-hybrid-manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            command = [
                "python3",
                str(ROOT / "scripts" / "model" / "validate-orcarouter-hybrid.py"),
                "--h3-source-reuse-check",
                "--h3-dir",
                str(h3),
            ]
            good = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("safely replaces the mazinb build-time source", good.stdout)

            manifest["overlay_revision"] = "0" * 40
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            bad = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("not pinned mazinb f2c21eb", bad.stdout)

    def test_hybrid_installer_reuses_pinned_h3_without_mazinb_download(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        preparer = (ROOT / "scripts" / "model" / "prepare-orcarouter-hybrid.sh").read_text(
            encoding="utf-8"
        )
        validator = (ROOT / "scripts" / "model" / "validate-orcarouter-hybrid.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("HYBRID_REUSE_H3=0", installer)
        self.assertIn("Pinned H3 provenance is reusable", installer)
        self.assertIn('if [[ "${HYBRID_REUSE_H3}" != 1 ]]; then', installer)
        self.assertIn("--runtime-only", installer)
        self.assertIn("reuse-check", preparer)
        self.assertIn("--h3-source-reuse-check", preparer)
        self.assertIn('MAZINB_REVISION = "f2c21eb"', validator)

    def test_hybrid_installer_checks_combined_source_disk_capacity(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        downloader = (ROOT / "scripts" / "download-weights.sh").read_text(encoding="utf-8")

        self.assertIn("--required-bytes", downloader)
        self.assertIn("PRINT_REQUIRED_BYTES", downloader)
        self.assertIn("base_required_bytes", installer)
        self.assertIn("overlay_required_bytes", installer)
        self.assertIn("Hybrid combined disk preflight passed", installer)
        self.assertIn("insufficient disk space for hybrid source checkpoints", installer)

    def test_direct_hybrid_download_is_rejected_as_generated_profile(self) -> None:
        result = subprocess.run(
            [str(ROOT / "scripts" / "download-weights.sh"), "--check"],
            cwd=ROOT,
            env={**os.environ, "MODEL_PROFILE": "orcarouter-hybrid"},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("generated locally", result.stderr)

    def test_installer_wires_hybrid_build_orchestrator(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("prepare-orcarouter-hybrid.sh", installer)
        self.assertIn("MODEL_PROFILE=orcarouter", installer)
        self.assertIn("MODEL_PROFILE=mazinb", installer)
        self.assertIn("H6_W4A16_MODEL_DIR", installer)
        self.assertIn("OrcaRouter Hybrid H6 (OrcaRouter + mazinb experts, W4A16 NVFP4)", installer)

    def test_installer_builds_local_v029_image_for_mazinb(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn('"${MODEL_PROFILE}" == mazinb', installer)
        self.assertIn('"${IMAGE}" == vllm-orcarouter-v029:v1', installer)
        self.assertIn("Dockerfile.v029-orcarouter", installer)

    def test_unknown_profile_fails(self) -> None:
        result = self.run_install("unknown")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown model profile", result.stderr)

    def test_dry_run_can_preview_another_installed_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state" / "qwen38-spark"
            state.mkdir(parents=True)
            (state / "install.env").write_text(
                "\n".join([
                    "SCHEMA_VERSION=2",
                    "PHASE=complete",
                    f"INSTALL_ROOT={ROOT}",
                    "MODEL_PROFILE=orcarouter",
                    "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                    f"MODEL_DIR={home / 'model'}",
                    "MODEL_OWNED=0",
                    "SWAP_FILE=/swap-ple.img",
                    "SWAP_OWNED=0",
                    "VLLM_IMAGE=test-image",
                    "IMAGE_OWNED=0",
                    "CONTAINER_NAME=qwen38-flash-next",
                    "CONFIG_OVERRIDE=",
                    "CONFIG_OWNED=0",
                    "MONITOR_PROTECT=0",
                    "PROXY_ENABLED=0",
                    "PROXY_OWNED=0",
                    "PROXY_PORT=8000",
                    "SERVICE_ENABLED=1",
                    "SERVICE_OWNED=1",
                    "UI_LANG=en",
                    "",
                ]),
                encoding="utf-8",
            )
            result = subprocess.run(
                [str(ROOT / "install.sh"), "--model", "nvidia", "--lang", "en", "--yes", "--no-start", "--dry-run"],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("profile     : nvidia", result.stdout)
            self.assertNotIn("Resuming installation", result.stdout)

    def test_refresh_profile_defaults_previews_new_orcarouter_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state" / "qwen38-spark"
            state.mkdir(parents=True)
            (state / "install.env").write_text(
                "\n".join([
                    "SCHEMA_VERSION=4",
                    "PHASE=complete",
                    f"INSTALL_ROOT={ROOT}",
                    "MODEL_PROFILE=orcarouter",
                    "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                    f"MODEL_DIR={home / 'model'}",
                    "MODEL_OWNED=0",
                    "SWAP_FILE=/swap-ple.img",
                    "SWAP_OWNED=0",
                    "VLLM_IMAGE=vllm/vllm-openai:qwen38-flash-next-arm64-cu130",
                    "IMAGE_OWNED=0",
                    "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "CONTAINER_NAME=qwen38-flash-next",
                    f"CONFIG_OVERRIDE={home / 'config.vllm.json'}",
                    "CONFIG_OWNED=1",
                    "MONITOR_PROTECT=0",
                    "MONITOR_ENABLED=0",
                    "MONITOR_MIN_AVAILABLE_GIB=6",
                    "MONITOR_MIN_FREE_GIB=2",
                    "MONITOR_FREE_GATE_GIB=10",
                    "MONITOR_MIN_SWAP_FREE_GIB=8",
                    "MONITOR_CONSECUTIVE=5",
                    "MONITOR_HEARTBEAT=60",
                    "API_ACCESS_MODE=docker",
                    "API_DOCKER_PORT=8000",
                    "API_LAN_ADDRESS=",
                    "API_LAN_PORT=8001",
                    "PROXY_ENABLED=1",
                    "PROXY_OWNED=1",
                    "PROXY_PORT=8000",
                    "SERVICE_ENABLED=1",
                    "SERVICE_OWNED=1",
                    "SERVICE_UNIT=qwen38-flash-next.service",
                    "UI_LANG=en",
                    "",
                ]),
                encoding="utf-8",
            )
            (home / "config.vllm.json").write_text("{}", encoding="utf-8")
            before = (state / "install.env").read_bytes()
            result = subprocess.run(
                [
                    str(ROOT / "install.sh"),
                    "--model", "orcarouter",
                    "--lang", "en",
                    "--yes",
                    "--no-start",
                    "--refresh-profile-defaults",
                    "--dry-run",
                ],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("vllm-skinny-tp1:v1", result.stdout)
            self.assertIn(
                "image change: vllm/vllm-openai:qwen38-flash-next-arm64-cu130 -> vllm-skinny-tp1:v1",
                result.stdout,
            )
            self.assertEqual((state / "install.env").read_bytes(), before)

    def test_refresh_profile_defaults_requires_manifest(self) -> None:
        result = self.run_install("orcarouter")
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = subprocess.run(
                [
                    str(ROOT / "install.sh"),
                    "--model", "orcarouter",
                    "--lang", "en",
                    "--yes",
                    "--no-start",
                    "--refresh-profile-defaults",
                    "--dry-run",
                ],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires an existing installation manifest", result.stderr)


if __name__ == "__main__":
    unittest.main()
