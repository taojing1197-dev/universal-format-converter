# Conversion matrix

Run `python3 scripts/convert_file.py --check --json` to see locally available engines.

| From | To | Preferred engine | Important limitation |
|---|---|---|---|
| PDF | DOCX | `pdf2docx` | Reconstructed layout; scanned pages need OCR |
| PDF | PNG/JPEG | PyMuPDF or Poppler | One image per page; no editability |
| PDF | TXT | `pypdf` | Reading order can differ from visual order |
| DOCX/PPTX/XLSX | PDF | LibreOffice | Fonts and platform-specific layout may shift |
| DOCX | TXT | `python-docx` | Images and most layout are discarded |
| Images | PDF | Pillow | Raster pages; no searchable text without OCR |
| PNG/JPEG/WebP | PNG/JPEG/WebP | Pillow | JPEG loses transparency and introduces loss |
| TXT/MD | TXT/MD | built-in | Content copy only; no rich formatting |

Examples:

```bash
python3 scripts/convert_file.py input.pdf output.docx
python3 scripts/convert_file.py input.pdf pages.png --dpi 180
python3 scripts/convert_file.py input.docx output.pdf
python3 scripts/convert_file.py image.png image.webp --quality 85
```

The converter never installs dependencies automatically. Install only the engine needed for the requested pair.
