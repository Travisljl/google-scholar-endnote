# Google Scholar EndNote Skill

Generate EndNote `.enw` citation files for scholarly references.

This skill supports two practical workflows:

- Single paper: use Google Scholar in Chrome, click `Cite/引用`, then export `EndNote`.
- Batch title list: convert a numbered `.txt` list of titles into one `.enw` file per reference using Crossref, OpenAlex, and arXiv metadata.

## Files

- `SKILL.md`: Codex skill instructions.
- `scripts/batch_endnote_from_titles.py`: Batch converter for numbered title lists.
- `agents/openai.yaml`: Codex UI metadata.

## Batch Usage

Input format:

```text
[1] The Natural Flow Regime
[2] Basic principles and ecological consequences of altered flow regimes for aquatic biodiversity
```

Run:

```bash
python3 scripts/batch_endnote_from_titles.py references.txt output-endnote
```

Outputs:

- `001_Title.enw`, `002_Title.enw`, etc.
- `manifest.csv` with match source, DOI, year, score, and output filename.
- `unmatched_titles.txt` for entries that need manual repair.

## Notes

- Raw Google Scholar citation links can return `403 Forbidden` outside the browser session, so single-paper Scholar exports should be done through Chrome.
- The batch script is faster and more stable for long lists because it avoids repeatedly opening Scholar.
- Always inspect `manifest.csv` and review low-score matches before treating a large batch as final.

## Validation

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```
