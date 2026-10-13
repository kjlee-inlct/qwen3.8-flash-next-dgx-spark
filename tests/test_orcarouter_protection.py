"""Synthetic tests prove OrcaRouter checkpoint remove/retire cannot execute."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
MANAGER=ROOT/"scripts/manage-models.sh"

class OrcaRouterProtectionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home=Path(temp.name)
        self.model=self.home/"models"/"qwen3.8-flash-next-orcarouter"
        self.model.mkdir(parents=True)
        self.marker=self.model/"weights.safetensors"
        self.marker.write_bytes(b"LEAVE UNCHANGED")
        self.env={**os.environ,"HOME":str(self.home),"XDG_STATE_HOME":str(self.home/"state")}

    def run_manager(self,*args):
        return subprocess.run(["bash",str(MANAGER),*args],env=self.env,cwd=ROOT,
            text=True,capture_output=True,check=False,timeout=12)

    def test_remove_protected_path_even_with_yes(self):
        result=self.run_manager("remove",str(self.model),"--yes")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("ORCAROUTER_PROTECTED",result.stderr)
        self.assertEqual(self.marker.read_bytes(),b"LEAVE UNCHANGED")

    def test_retire_protected_profile_even_with_yes(self):
        result=self.run_manager("retire","orcarouter","--yes")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("ORCAROUTER_PROTECTED",result.stderr)
        self.assertEqual(self.marker.read_bytes(),b"LEAVE UNCHANGED")

if __name__=="__main__":
    unittest.main()
