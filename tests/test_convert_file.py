import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "convert_file.py"


def load_converter_module():
    spec = importlib.util.spec_from_file_location("convert_file", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def test_page_output_set_ignores_similar_unrelated_files(self):
        converter = load_converter_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.pdf"
            output = root / "pages.png"
            numbered = root / "pages-001.png"
            unrelated = root / "pages-1-backup.png"
            source.write_bytes(b"pdf")
            numbered.write_bytes(b"page")
            unrelated.write_bytes(b"keep")
            self.assertEqual(converter.page_output_set(source, output), [numbered])

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

    def test_empty_output_set_is_rejected(self):
        converter = load_converter_module()
        with self.assertRaisesRegex(RuntimeError, "produced no output"):
            converter.validate_outputs([])

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

    def test_input_cannot_be_overwritten_in_place_even_with_force(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("keep me", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), str(source), "--force"],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("must be different paths", result.stderr)
            self.assertEqual(source.read_text(encoding="utf-8"), "keep me")

    def test_office_conversion_does_not_overwrite_intermediate_name_collision(self):
        converter = load_converter_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.docx"
            output = root / "renamed.pdf"
            collision = root / "source.pdf"
            source.write_bytes(b"document")
            collision.write_bytes(b"keep me")

            def fake_run(command, check):
                self.assertTrue(check)
                outdir = Path(command[command.index("--outdir") + 1])
                (outdir / "source.pdf").write_bytes(b"converted")

            with mock.patch.object(converter.shutil, "which", return_value="/usr/bin/soffice"), mock.patch.object(converter.subprocess, "run", side_effect=fake_run):
                produced = converter.office_to_pdf(source, output, {"libreoffice": True})

            self.assertEqual(produced, [output])
            self.assertEqual(output.read_bytes(), b"converted")
            self.assertEqual(collision.read_bytes(), b"keep me")


if __name__ == "__main__":
    unittest.main()
