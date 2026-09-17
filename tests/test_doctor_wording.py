from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
DOCTOR = ROOT / "scripts" / "doctor.sh"


class DoctorWordingTests(unittest.TestCase):
    def test_doctor_uses_generic_api_access_wording(self) -> None:
        doctor = DOCTOR.read_text(encoding="utf-8")

        self.assertIn('pass "managed API access socket is active"', doctor)
        self.assertIn('fail "managed API access was selected but its socket is not active"', doctor)
        self.assertNotIn('pass "OpenWebUI proxy socket is active"', doctor)
        self.assertNotIn('fail "OpenWebUI proxy was selected but is not active"', doctor)

        # Internal compatibility identifiers remain intentionally unchanged.
        self.assertIn("qwen38-openwebui-proxy.socket", doctor)
        self.assertIn("PROXY_ENABLED", doctor)


if __name__ == "__main__":
    unittest.main()
