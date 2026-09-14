import subprocess
import unittest


class ProxyUnitParsingTests(unittest.TestCase):
    def test_extracts_port_from_listen_stream(self):
        unit = "[Socket]\nListenStream=172.17.0.1:8000\nNoDelay=true\n"
        command = [
            "awk",
            "-F[=:]",
            '$1=="ListenStream" {print $NF}',
        ]
        result = subprocess.run(command, input=unit, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "8000")


if __name__ == "__main__":
    unittest.main()
