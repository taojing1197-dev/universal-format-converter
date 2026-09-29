# Universal Format Converter

A Codex skill with a portable CLI for safe conversions among PDF, Word, images, text, and common office files.

The converter detects available engines, refuses accidental overwrites, preserves the source, and verifies that outputs exist and are non-empty. Conversion engines are optional so users install only what they need.
Input and output must resolve to different paths, including when `--force` is used.
Office conversions use an isolated temporary output directory so a source-named PDF beside the requested destination is never overwritten as an intermediate file.
PDF page-set cleanup only treats strictly numbered siblings as generated pages, preserving similarly named unrelated files.

Optional Python engines are listed in `requirements-optional.txt`. LibreOffice enables office-to-PDF conversion, while Poppler provides a PDF-to-image fallback.

## Use

```bash
python3 scripts/convert_file.py --check
python3 scripts/convert_file.py input.pdf output.docx
python3 scripts/convert_file.py input.pdf pages.png --dpi 180
python3 scripts/convert_file.py image.png image.webp --quality 85
```

See `references/conversion-matrix.md` for supported pairs and fidelity limits.

## Test

```bash
python3 -m unittest discover -s tests -v
```

Contributions for additional deterministic conversion engines and validation checks are welcome.

## License

MIT
