import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "convert_file.py"


class ConverterTests(unittest.TestCase):
    def test_capability_report(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--check", "--json"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("pillow", json.loads(result.stdout))

    def test_text_copy_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            output = Path(directory) / "output.md"
            source.write_text("hello", encoding="utf-8")
            first = subprocess.run([sys.executable, str(SCRIPT), str(source), str(output)], text=True, capture_output=True)
            second = subprocess.run([sys.executable, str(SCRIPT), str(source), str(output)], text=True, capture_output=True)
            self.assertEqual(first.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "hello")
            self.assertEqual(second.returncode, 1)


if __name__ == "__main__":
    unittest.main()
