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

    def test_pdf_page_set_collision_is_guarded(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.pdf"
            output = Path(directory) / "pages.png"
            existing_page = Path(directory) / "pages-001.png"
            source.write_bytes(b"not needed because collision is detected first")
            existing_page.write_bytes(b"existing")
            result = subprocess.run([sys.executable, str(SCRIPT), str(source), str(output)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("page output already exists", result.stderr)
            self.assertEqual(existing_page.read_bytes(), b"existing")

    def test_pdf_render_rejects_unsupported_image_format(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.pdf"
            output = Path(directory) / "output.webp"
            source.write_bytes(b"format routing happens before PDF parsing")
            result = subprocess.run([sys.executable, str(SCRIPT), str(source), str(output)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("supports PNG or JPEG", result.stderr)

    def test_invalid_quality_is_rejected(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--check", "--quality", "101"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--quality must be between 1 and 100", result.stderr)

    def test_force_preserves_existing_pages_when_conversion_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "invalid.pdf"
            output = Path(directory) / "pages.png"
            existing_page = Path(directory) / "pages-001.png"
            source.write_bytes(b"invalid pdf")
            existing_page.write_bytes(b"keep me")
            result = subprocess.run([sys.executable, str(SCRIPT), str(source), str(output), "--force"], text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(existing_page.read_bytes(), b"keep me")


if __name__ == "__main__":
    unittest.main()
