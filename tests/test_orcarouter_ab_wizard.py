"""OrcaRouter A/B wizard: clean-host defaults and read-only preview, not live GPU qualification."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
V029="vllm-orcarouter-v029:v1"
LEGACY="vllm-skinny-tp1:v1"
class OrcaRouterABWizardTests(unittest.TestCase):
    def run_clean(self,*args,answers=None):
        with tempfile.TemporaryDirectory() as d:
            env={**os.environ,"HOME":d,"XDG_STATE_HOME":d+"/state"}
            for k in ("MODEL_PROFILE","QWEN38_MODEL_ROOT","MONITOR_ENABLED","MONITOR_PROTECT"): env.pop(k,None)
            return subprocess.run([str(ROOT/"install.sh"),*args,"--dry-run"],cwd=ROOT,env=env,input=answers,text=True,capture_output=True)
    def test_clean_default_v029_monitor_protected(self):
        r=self.run_clean("--model","orcarouter","--lang","en","--yes","--no-start")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn("image       : "+V029,r.stdout)
        self.assertIn("monitor     : enabled",r.stdout)
        self.assertIn("protection  : enabled",r.stdout)
        self.assertIn("DRY-RUN complete",r.stdout)
    def test_interactive_legacy_variant(self):
        r=self.run_clean("--lang","en","--no-start",answers="L\n\nn\ny\ny\nn\n1\ny\ny\n")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn("image       : "+LEGACY,r.stdout)
        self.assertIn("protection  : enabled",r.stdout)
    def test_plan_only(self):
        r=subprocess.run(["bash",str(ROOT/"scripts/lib/orcarouter-ab-plan.sh"),"--installed-image",LEGACY],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        for key in ("A_IMAGE="+LEGACY,"B_IMAGE="+V029,"BENCHMARK_STATUS=NOT_MEASURED","WIZARD_ISOLATED_START=NOT_IMPLEMENTED"):
            self.assertIn(key,r.stdout)
    def test_builder_preflight_and_h38_independent(self):
        installer=(ROOT/"install.sh").read_text()
        self.assertIn('"${IMAGE}" == '+V029,installer)
        self.assertIn('Dockerfile.v029-orcarouter',installer)
        self.assertIn('Dockerfile.skinny-gemm',installer)
        pre=(ROOT/"scripts/runtime/preflight-runtime.sh").read_text()
        self.assertIn('BASE_V029_IMAGE="'+V029+'"',pre)
        serve=(ROOT/"scripts/serve.sh").read_text()
        self.assertIn('IMAGE="${VLLM_IMAGE:-'+V029+'}"',serve)
        coord=(ROOT/"scripts/lifecycle/release-profile-refresh-transition.sh").read_text()
        self.assertIn('TARGET_IMAGE="${TARGET_H38_IMAGE}"',coord)
        self.assertNotIn('TARGET_IMAGE="${PROFILE_IMAGE}"',coord)
