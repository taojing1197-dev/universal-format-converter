---
name: universal-format-converter
description: Convert files between PDF, Word, images, text, and common office formats while preserving the source, selecting a fidelity-appropriate engine, and validating the result. Use when the user asks to convert or batch-convert files; do not use for ordinary content editing.
---

# Universal Format Converter

Choose the conversion path based on the user's real goal: editable content, visual fidelity, searchable text, or smaller files. No single engine preserves every property.

## Workflow

1. Inspect the input type, page count or dimensions, and whether it contains scans, forms, tables, transparency, or animation.
2. Read [references/conversion-matrix.md](references/conversion-matrix.md) for the requested pair and required engine.
3. Preserve the source. Refuse to overwrite an existing output unless the user explicitly requests replacement.
4. Run `scripts/convert_file.py --check` before conversion when dependencies are uncertain.
5. Convert, then validate the output by reopening it. For layout-sensitive PDF results, render representative pages and visually inspect them.

## Fidelity rules

- PDF to Word is reconstruction, not lossless conversion. Scans need OCR; complex columns, forms, and tables require manual review.
- Word or office files to PDF should use LibreOffice or the native office application when layout matters.
- PDF to images preserves appearance but loses editability and searchable structure.
- JPEG is lossy and has no transparency. Use PNG for text-heavy screenshots or transparency, and WebP when size matters and compatibility is acceptable.
- Animated images, layered files, embedded media, macros, signatures, and fillable forms need format-specific handling; never silently flatten or discard them.

## Deliverable

Report the engine used, output files, fidelity limitations, and validation performed. Do not claim a conversion is complete merely because a command exited successfully.
