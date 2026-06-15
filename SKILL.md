---
name: google-scholar-endnote
description: Download or generate EndNote citation files for scholarly references. Use when the user asks to search Google Scholar for a paper, export/download an EndNote citation, save .enw files, batch-convert a numbered TXT list of paper titles into EndNote files, or reproduce a Google Scholar cite-to-EndNote workflow.
---

# Google Scholar EndNote

## Overview

Create EndNote `.enw` citation files for one paper or a batch of paper titles. Use the browser-based Google Scholar workflow for single items that must come from Scholar; use the bundled batch script for long title lists to avoid slow, CAPTCHA-prone manual Scholar exports.

## Decision Tree

- For one paper or a small ambiguous set: use Chrome and Google Scholar.
- For a `.txt` file with many titles: use `scripts/batch_endnote_from_titles.py`.
- For any low-confidence or missing batch results: repair with DOI/arXiv/manual exact lookup, then fall back to Scholar only for the remaining few.

## Single-Paper Scholar Workflow

1. Use the `Chrome` plugin (`chrome:control-chrome`) for the actual Google Scholar workflow and download.
2. Navigate to `https://scholar.google.com/scholar?q="<paper title>"`.
3. Verify the visible title, authors, publication venue, and year.
4. Click the target result's `引用` or `Cite` button, then click `EndNote`.
5. Check `~/Downloads` for the new `.enw`, often named `scholar.enw`.
6. Inspect the file to ensure it starts with EndNote tags such as `%0`, `%T`, `%A`, `%J`, `%D`.
7. Rename it to a safe title-based filename.

Do not use raw `curl` as the primary Scholar download method. Google Scholar citation URLs can return `403 Forbidden` outside the browser session. If the in-app Browser says downloads are unsupported, switch to Chrome.

## Batch TXT Workflow

Use the bundled script when the user provides a numbered title list such as:

```text
[1] The Natural Flow Regime
[2] Basic principles and ecological consequences of altered flow regimes for aquatic biodiversity
```

Run:

```bash
python3 /path/to/google-scholar-endnote/scripts/batch_endnote_from_titles.py <titles.txt> <output-dir>
```

The script:

- Parses lines matching `[number] title`.
- Searches Crossref first, then OpenAlex, then arXiv.
- Writes one `.enw` file per matched title, using the original number as a three-digit filename prefix.
- Writes `manifest.csv` with status, query title, matched title, score, source, DOI, year, file, and notes.
- Writes `unmatched_titles.txt` for titles that need repair or manual Scholar lookup.

After a batch run, verify:

```bash
python3 - <<'PY'
import csv, pathlib, re
folder = pathlib.Path("<output-dir>").expanduser()
files = sorted(folder.glob("*.enw"))
rows = list(csv.DictReader((folder / "manifest.csv").open(encoding="utf-8")))
indices = [int(re.match(r"(\d{3})_", p.name).group(1)) for p in files if re.match(r"(\d{3})_", p.name)]
print("enw_files", len(files))
print("manifest_rows", len(rows))
print("manifest_ok", sum(r["status"] == "ok" for r in rows))
print("manifest_unmatched", sum(r["status"] != "ok" for r in rows))
print("html_error_files", [p.name for p in files if p.read_text(encoding="utf-8", errors="ignore").lstrip().startswith("<!DOCTYPE html>")])
print("invalid_enw_files", [p.name for p in files if not p.read_text(encoding="utf-8", errors="ignore").startswith("%0 ")][:10])
print("duplicate_indices", sorted({i for i in indices if indices.count(i) > 1}))
PY
```

## Repair Strategy

- Treat scores below `0.90` as review candidates, especially short/generic titles.
- Delete or replace obvious false-positive files before final delivery.
- For missed DOI-backed articles, look up by DOI through Crossref or OpenAlex and rewrite the `.enw`.
- For arXiv-style classics, use the arXiv API and write `%0 Preprint`, `%J arXiv`, `%R 10.48550/arXiv.<id>`, `%U https://arxiv.org/abs/<id>`.
- Keep `unmatched_titles.txt` empty only after every row has a valid `.enw`.

## Final Report

Report the output folder, the number of `.enw` files, manifest status counts, and any remaining unmatched or low-confidence items. Mention if the result was generated from Crossref/OpenAlex/arXiv rather than downloaded directly from Scholar.
