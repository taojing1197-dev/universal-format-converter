#!/usr/bin/env python3
"""Portable front end for common document and image conversions."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
PDF_RENDER_TYPES = {".png", ".jpg", ".jpeg"}
OFFICE_TYPES = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".odt", ".ods", ".odp"}
TEXT_TYPES = {".txt", ".md"}


def capabilities() -> dict[str, bool]:
    return {
        "pillow": importlib.util.find_spec("PIL") is not None,
        "pymupdf": importlib.util.find_spec("fitz") is not None,
        "pypdf": importlib.util.find_spec("pypdf") is not None,
        "pdf2docx": importlib.util.find_spec("pdf2docx") is not None,
        "python_docx": importlib.util.find_spec("docx") is not None,
        "libreoffice": bool(shutil.which("soffice") or shutil.which("libreoffice")),
        "pdftoppm": bool(shutil.which("pdftoppm")),
    }


def ensure_output_available(output: Path, force: bool) -> None:
    if output.exists() and not force:
        raise FileExistsError(f"output already exists: {output}; use --force to replace it")
    output.parent.mkdir(parents=True, exist_ok=True)


def page_output_set(source: Path, output: Path) -> list[Path]:
    if source.suffix.lower() != ".pdf" or output.suffix.lower() not in IMAGE_TYPES:
        return []
    numbered = sorted(output.parent.glob(f"{output.stem}-[0-9]*{output.suffix}"))
    return ([output] if output.exists() else []) + numbered


def prepare_outputs(source: Path, output: Path, force: bool) -> list[Path]:
    """Protect both the requested path and numbered PDF page outputs."""
    ensure_output_available(output, force)
    collisions = page_output_set(source, output)
    if collisions and not force:
        rendered = ", ".join(str(path) for path in collisions[:5])
        raise FileExistsError(f"page output already exists: {rendered}; use --force to replace the page set")
    return collisions


def image_convert(source: Path, output: Path, quality: int) -> list[Path]:
    from PIL import Image

    with Image.open(source) as image:
        target = image
        if output.suffix.lower() in {".jpg", ".jpeg"} and image.mode not in {"RGB", "L"}:
            background = Image.new("RGB", image.size, "white")
            if "A" in image.getbands():
                background.paste(image, mask=image.getchannel("A"))
            else:
                background.paste(image)
            target = background
        target.save(output, quality=quality)
    return [output]


def images_to_pdf(source: Path, output: Path) -> list[Path]:
    from PIL import Image

    with Image.open(source) as image:
        frame = image.convert("RGB")
        frame.save(output, "PDF", resolution=150.0)
    return [output]


def pdf_to_images(source: Path, output: Path, dpi: int, caps: dict[str, bool]) -> list[Path]:
    produced: list[Path] = []
    if caps["pymupdf"]:
        import fitz

        document = fitz.open(source)
        scale = dpi / 72
        for page_number, page in enumerate(document, 1):
            target = output if len(document) == 1 else output.with_name(f"{output.stem}-{page_number:03d}{output.suffix}")
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=output.suffix.lower() == ".png")
            if output.suffix.lower() in {".jpg", ".jpeg"}:
                pixmap.save(str(target), output="jpeg")
            else:
                pixmap.save(str(target))
            produced.append(target)
        document.close()
        return produced
    if caps["pdftoppm"]:
        prefix = output.with_suffix("")
        fmt = "jpeg" if output.suffix.lower() in {".jpg", ".jpeg"} else "png"
        subprocess.run(["pdftoppm", f"-{fmt}", "-r", str(dpi), str(source), str(prefix)], check=True)
        return sorted(output.parent.glob(f"{prefix.name}-*.{ 'jpg' if fmt == 'jpeg' else 'png' }"))
    raise RuntimeError("PDF-to-image needs PyMuPDF or pdftoppm")


def pdf_to_text(source: Path, output: Path) -> list[Path]:
    from pypdf import PdfReader

    text = "\n\n".join((page.extract_text() or "") for page in PdfReader(str(source)).pages)
    output.write_text(text, encoding="utf-8")
    return [output]


def pdf_to_docx(source: Path, output: Path) -> list[Path]:
    from pdf2docx import Converter

    converter = Converter(str(source))
    try:
        converter.convert(str(output))
    finally:
        converter.close()
    return [output]


def docx_to_text(source: Path, output: Path) -> list[Path]:
    from docx import Document

    document = Document(str(source))
    output.write_text("\n".join(paragraph.text for paragraph in document.paragraphs), encoding="utf-8")
    return [output]


def office_to_pdf(source: Path, output: Path, caps: dict[str, bool]) -> list[Path]:
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if not executable or not caps["libreoffice"]:
        raise RuntimeError("office-to-PDF needs LibreOffice")
    with tempfile.TemporaryDirectory(prefix=".format-converter-", dir=output.parent) as directory:
        temporary_output = Path(directory)
        subprocess.run([executable, "--headless", "--convert-to", "pdf", "--outdir", str(temporary_output), str(source)], check=True)
        generated = temporary_output / f"{source.stem}.pdf"
        if not generated.is_file():
            raise RuntimeError("LibreOffice did not produce the expected PDF")
        generated.replace(output)
    return [output]


def convert(source: Path, output: Path, args: argparse.Namespace, caps: dict[str, bool]) -> list[Path]:
    source_type, output_type = source.suffix.lower(), output.suffix.lower()
    if source_type in TEXT_TYPES and output_type in TEXT_TYPES:
        output.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return [output]
    if source_type in IMAGE_TYPES and output_type in IMAGE_TYPES:
        if not caps["pillow"]:
            raise RuntimeError("image conversion needs Pillow")
        return image_convert(source, output, args.quality)
    if source_type in IMAGE_TYPES and output_type == ".pdf":
        if not caps["pillow"]:
            raise RuntimeError("image-to-PDF needs Pillow")
        return images_to_pdf(source, output)
    if source_type == ".pdf" and output_type in PDF_RENDER_TYPES:
        return pdf_to_images(source, output, args.dpi, caps)
    if source_type == ".pdf" and output_type in IMAGE_TYPES:
        raise RuntimeError("PDF rendering supports PNG or JPEG output; render to PNG before converting to another image format")
    if source_type == ".pdf" and output_type == ".txt":
        if not caps["pypdf"]:
            raise RuntimeError("PDF-to-text needs pypdf")
        return pdf_to_text(source, output)
    if source_type == ".pdf" and output_type == ".docx":
        if not caps["pdf2docx"]:
            raise RuntimeError("PDF-to-DOCX needs pdf2docx")
        return pdf_to_docx(source, output)
    if source_type == ".docx" and output_type == ".txt":
        if not caps["python_docx"]:
            raise RuntimeError("DOCX-to-text needs python-docx")
        return docx_to_text(source, output)
    if source_type in OFFICE_TYPES and output_type == ".pdf":
        return office_to_pdf(source, output, caps)
    raise RuntimeError(f"unsupported conversion: {source_type or '(none)'} -> {output_type or '(none)'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--check", action="store_true", help="show available conversion engines")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument("--quality", type=int, default=85)
    args = parser.parse_args()
    if args.dpi <= 0:
        parser.error("--dpi must be greater than zero")
    if not 1 <= args.quality <= 100:
        parser.error("--quality must be between 1 and 100")
    caps = capabilities()
    if args.check:
        print(json.dumps(caps, indent=2) if args.as_json else "\n".join(f"{key}: {'yes' if value else 'no'}" for key, value in caps.items()))
        return 0
    if args.input is None or args.output is None:
        parser.error("input and output are required unless --check is used")
    source, output = args.input.expanduser().resolve(), args.output.expanduser().resolve()
    if not source.is_file():
        print(f"error: input not found: {source}", file=sys.stderr)
        return 2
    if source == output:
        print("error: input and output must be different paths", file=sys.stderr)
        return 2
    try:
        previous_outputs = prepare_outputs(source, output, args.force)
        produced = convert(source, output, args, caps)
        missing = [path for path in produced if not path.is_file() or path.stat().st_size == 0]
        if missing:
            raise RuntimeError(f"conversion produced missing or empty output: {missing}")
        if args.force:
            produced_set = set(produced)
            for stale in previous_outputs:
                if stale not in produced_set and stale.exists():
                    stale.unlink()
    except (FileExistsError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps([str(path) for path in produced], indent=2) if args.as_json else "\n".join(str(path) for path in produced))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
