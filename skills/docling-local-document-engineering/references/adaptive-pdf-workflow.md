# Adaptive Local PDF Workflow

## Readiness and Source Record

Confirm local tools before conversion:

```powershell
Get-Command docling
docling --version
docling convert --help
```

For reusable output, record the absolute source path, byte size, physical page count, and SHA-256:

```powershell
Get-Item -LiteralPath $source | Select-Object FullName,Length
Get-FileHash -Algorithm SHA256 -LiteralPath $source
```

Do not modify the original PDF. Put one-off intermediates in a task-local temporary directory.

## Choose the Extraction Route

Inspect representative pages before choosing:

- **Native text, simple layout, short document:** prefer direct extraction when copied text is
  complete and ordered correctly. Render the relevant original pages with `pdf:pdf`.
- **Scanned or mixed pages:** use Docling OCR. Use full OCR only when the embedded text is missing or
  materially wrong; OCR can replace correct characters with errors.
- **Tables, figures, formulas, or multi-column layout:** use Docling structure and JSON provenance,
  then inspect the original page visually.
- **Long documents:** convert by bounded page ranges or use a resumable corpus workflow rather than
  holding the full document in agent context.

## One-Off Docling Conversion

Use the local CLI and current `--help`; do not assume options from another Docling version.

```powershell
$output = Join-Path $env:TEMP "docling-task-output"
New-Item -ItemType Directory -Force -Path $output | Out-Null
docling convert $source --to md --to json --image-export-mode referenced `
  --output $output --abort-on-error --device cuda
```

For a true scanned document, add `--ocr-mode full_page`. For selected evidence, add a one-based
`--page-range`, such as `12-18`. Do not force full-page OCR over trustworthy native text.

Markdown is convenient for reading; JSON carries structural and provenance detail. Check that each
candidate statement maps to the expected physical page. A generated sequence number or chunk ID is
not a PDF page number.

Treat empty output, missing requested formats, or missing page coverage as conversion failure even
when output files were created. Do not publish or answer from those artifacts.

If Docling is unavailable, state the limitation and use direct extraction plus rendered-page review
when possible. Do not install, enable remote models, or send documents to a service without task
authorization.

## Evidence Gate

Render and inspect the hash-matched original PDF page for critical numbers, specifications, tables,
figures, equations, footnotes, signatures, security claims, or any OCR/layout warning. Inspect
adjacent pages when a table, figure, or section crosses a boundary. If extraction and the original
page disagree, the original PDF wins and the discrepancy must be reported.

Before retaining derived output, verify readable UTF-8, expected page coverage, valid referenced
images, and an unchanged SHA-256. Remove task-local intermediates after the result is delivered.
