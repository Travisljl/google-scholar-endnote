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

---

# Google Scholar EndNote Skill 中文说明

这个 skill 用来为学术文献生成 EndNote `.enw` 引用文件。

它支持两种常用流程：

- 单篇文献：在 Chrome 中打开 Google Scholar，点击 `Cite/引用`，再导出 `EndNote`。
- 批量题名列表：把带编号的 `.txt` 文献题名列表批量转换成 `.enw` 文件，每条文献生成一个文件，元数据来自 Crossref、OpenAlex 和 arXiv。

## 文件结构

- `SKILL.md`：Codex 使用的 skill 指令。
- `scripts/batch_endnote_from_titles.py`：用于批量转换题名列表的脚本。
- `agents/openai.yaml`：Codex UI 元数据。

## 批量使用方法

输入文件格式示例：

```text
[1] The Natural Flow Regime
[2] Basic principles and ecological consequences of altered flow regimes for aquatic biodiversity
```

运行命令：

```bash
python3 scripts/batch_endnote_from_titles.py references.txt output-endnote
```

输出内容：

- `001_Title.enw`、`002_Title.enw` 等 EndNote 引用文件。
- `manifest.csv`：记录匹配来源、DOI、年份、匹配分数和输出文件名。
- `unmatched_titles.txt`：记录需要人工修复或进一步核验的条目。

## 注意事项

- Google Scholar 的引用链接直接用 `curl` 访问时可能返回 `403 Forbidden`，所以单篇 Scholar 导出应通过 Chrome 浏览器完成。
- 批量转换时优先使用脚本，比逐条打开 Google Scholar 更快、更稳定，也更不容易触发验证码。
- 大批量结果完成后，建议检查 `manifest.csv`，尤其关注低分匹配项，确认没有误匹配。

## 校验

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```
