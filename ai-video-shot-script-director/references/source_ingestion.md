# Source Document Ingestion

The source may be a modern document, a legacy OLE Word `.doc`, rich text, a spreadsheet-like table exported as text, or plain prose. Extraction is evidence intake, not creative interpretation.

## Required procedure

1. Hash the original readable bytes before conversion.
2. For `.doc`, `.rtf`, and `.docx` on macOS, use `textutil -convert txt -stdout` first. For `.docx`, the helper can fall back to deterministic `word/document.xml` extraction when `textutil` is unavailable.
3. Normalize encoding and control delimiters without sorting or reflowing cells. Legacy Word table cell delimiter `U+0007` becomes a tab; row and paragraph order remain unchanged.
4. Persist the extracted UTF-8 text and an extraction report containing source hash, method, byte count, detected ordered shot numbers, and time tokens.
5. Compare the detected shot order, timing tokens, and supplied copy with the visible source before professional expansion.
6. Register the original document as the source authority. The extracted text is a traceable derivative, not a replacement authority.

Use `scripts/extract_source_document.py`. Example:

```bash
python3 scripts/extract_source_document.py source.doc \
  --output work/source.extracted.txt \
  --report work/source.extraction.json
```

## Failure isolation

- A conversion failure is local to that document or unreadable field. Continue all unaffected director work.
- Never ask the user to rewrite a readable legacy document by hand.
- If only one table cell is corrupt, preserve its position, mark that field `partial`, and continue other rows.
- Do not recover exact copy, product claims, or timing from guesswork. Those isolated facts remain unavailable or blocked while inferred camera and staging work continues.
- Do not use lossy OCR when readable document bytes and deterministic conversion are available.

## Acceptance

- original file hash is recorded;
- extracted row/cell order is unchanged;
- every detected shot number and time token is reported in source order;
- supplied wording is preserved byte-for-byte after Unicode decoding, except documented line-ending and control-delimiter normalization;
- no professional directing decision is mixed into the extraction artifact.
