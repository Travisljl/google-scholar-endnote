#!/usr/bin/env python3
import csv
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path


USER_AGENT = "Codex batch EndNote citation export"
MIN_SCORE = 0.72
RETRIES = 3


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(x) for x in value if x)
    value = re.sub(r"<[^>]+>", "", str(value))
    return re.sub(r"\s+", " ", value).strip()


def normalize_title(value):
    value = unicodedata.normalize("NFKD", clean_text(value)).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[-‐‑‒–—_:;,.!?()[\]{}'\"“”‘’/\\\\]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def title_score(want, got):
    want_n = normalize_title(want)
    got_n = normalize_title(got)
    if not want_n or not got_n:
        return 0.0
    ratio = SequenceMatcher(None, want_n, got_n).ratio()
    if want_n in got_n or got_n in want_n:
        ratio = max(ratio, 0.90)
    return ratio


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise last_error


def get_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read().decode("utf-8")
        except Exception as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise last_error


def parse_titles(path):
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\[(\d+)\]\s+(.+?)\s*$", line)
        if match:
            items.append({"index": int(match.group(1)), "query_title": match.group(2)})
    return items


def year_from_parts(parts):
    if not parts:
        return ""
    date_parts = parts.get("date-parts") or []
    if date_parts and date_parts[0]:
        return str(date_parts[0][0])
    return ""


def crossref_search(title):
    params = urllib.parse.urlencode(
        {
            "query.title": title,
            "rows": 5,
            "select": "DOI,title,author,container-title,published-print,published-online,issued,volume,issue,page,publisher,ISSN,type,URL",
        }
    )
    url = f"https://api.crossref.org/works?{params}"
    data = get_json(url)
    candidates = data.get("message", {}).get("items", [])
    best = None
    for item in candidates:
        got_title = clean_text((item.get("title") or [""])[0])
        score = title_score(title, got_title)
        if best is None or score > best["score"]:
            best = {"score": score, "item": item, "title": got_title}
    if not best or best["score"] < MIN_SCORE:
        return None

    item = best["item"]
    authors = []
    for author in item.get("author") or []:
        given = clean_text(author.get("given"))
        family = clean_text(author.get("family"))
        name = " ".join(part for part in [family, given] if part)
        if name:
            authors.append(name)

    year = (
        year_from_parts(item.get("published-print"))
        or year_from_parts(item.get("published-online"))
        or year_from_parts(item.get("issued"))
    )
    return {
        "source": "Crossref",
        "score": best["score"],
        "type": item.get("type") or "journal-article",
        "title": best["title"],
        "authors": authors,
        "journal": clean_text((item.get("container-title") or [""])[0]),
        "year": year,
        "volume": clean_text(item.get("volume")),
        "issue": clean_text(item.get("issue")),
        "pages": clean_text(item.get("page")),
        "doi": clean_text(item.get("DOI")),
        "url": clean_text(item.get("URL")),
        "publisher": clean_text(item.get("publisher")),
        "issn": clean_text((item.get("ISSN") or [""])[0]),
    }


def openalex_search(title):
    params = urllib.parse.urlencode({"search": title, "per-page": 5})
    url = f"https://api.openalex.org/works?{params}"
    data = get_json(url)
    candidates = data.get("results", [])
    best = None
    for item in candidates:
        got_title = clean_text(item.get("title") or item.get("display_name"))
        score = title_score(title, got_title)
        if best is None or score > best["score"]:
            best = {"score": score, "item": item, "title": got_title}
    if not best or best["score"] < MIN_SCORE:
        return None

    item = best["item"]
    authors = []
    for authorship in item.get("authorships") or []:
        author = authorship.get("author") or {}
        name = clean_text(author.get("display_name"))
        if name:
            authors.append(name)
    primary = item.get("primary_location") or {}
    source = primary.get("source") or {}
    doi = clean_text(item.get("doi")).replace("https://doi.org/", "")
    biblio = item.get("biblio") or {}
    return {
        "source": "OpenAlex",
        "score": best["score"],
        "type": item.get("type") or "journal-article",
        "title": best["title"],
        "authors": authors,
        "journal": clean_text(source.get("display_name")),
        "year": str(item.get("publication_year") or ""),
        "volume": clean_text(biblio.get("volume")),
        "issue": clean_text(biblio.get("issue")),
        "pages": "-".join(part for part in [clean_text(biblio.get("first_page")), clean_text(biblio.get("last_page"))] if part),
        "doi": doi,
        "url": clean_text(primary.get("landing_page_url") or item.get("id")),
        "publisher": "",
        "issn": clean_text((source.get("issn") or [""])[0] if source.get("issn") else ""),
    }


def arxiv_search(title):
    params = urllib.parse.urlencode(
        {"search_query": f'ti:"{title}"', "start": 0, "max_results": 5}
    )
    data = get_text(f"http://export.arxiv.org/api/query?{params}")
    root = ET.fromstring(data)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    best = None
    for entry in root.findall("a:entry", ns):
        got_title = clean_text(entry.findtext("a:title", default="", namespaces=ns))
        score = title_score(title, got_title)
        if best is None or score > best["score"]:
            best = {"score": score, "entry": entry, "title": got_title}
    if not best or best["score"] < MIN_SCORE:
        return None

    entry = best["entry"]
    entry_id = entry.findtext("a:id", default="", namespaces=ns).rsplit("/", 1)[-1]
    arxiv_id = entry_id.split("v")[0]
    authors = [
        clean_text(author.findtext("a:name", default="", namespaces=ns))
        for author in entry.findall("a:author", ns)
    ]
    published = entry.findtext("a:published", default="", namespaces=ns)
    return {
        "source": "arXiv",
        "score": best["score"],
        "type": "preprint",
        "title": best["title"],
        "authors": [author for author in authors if author],
        "journal": "arXiv",
        "year": published[:4],
        "volume": "",
        "issue": "",
        "pages": "",
        "doi": f"10.48550/arXiv.{arxiv_id}",
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "publisher": "arXiv",
        "issn": "",
    }


def enw_type(meta_type):
    if meta_type in {"book", "monograph"}:
        return "Book"
    if meta_type in {"book-chapter", "book-section"}:
        return "Book Section"
    if meta_type in {"proceedings-article", "conference-paper"}:
        return "Conference Paper"
    if meta_type in {"preprint", "posted-content"}:
        return "Preprint"
    return "Journal Article"


def to_enw(meta):
    lines = [("%0", enw_type(meta.get("type"))), ("%T", meta.get("title", ""))]
    for author in meta.get("authors") or []:
        lines.append(("%A", author))
    fields = [
        ("%J", meta.get("journal", "")),
        ("%V", meta.get("volume", "")),
        ("%N", meta.get("issue", "")),
        ("%P", meta.get("pages", "")),
        ("%@", meta.get("issn", "")),
        ("%R", meta.get("doi", "")),
        ("%U", meta.get("url", "")),
        ("%D", meta.get("year", "")),
        ("%I", meta.get("publisher", "")),
    ]
    lines.extend(fields)
    return "\n".join(f"{tag} {clean_text(value)}" for tag, value in lines if clean_text(value)) + "\n"


def safe_filename(index, title):
    value = unicodedata.normalize("NFKD", title)
    value = re.sub(r"[^\w\s.-]", "", value, flags=re.UNICODE)
    value = re.sub(r"\s+", "_", value).strip("._")
    value = value[:120] or "untitled"
    return f"{index:03d}_{value}.enw"


def lookup(title):
    try:
        meta = crossref_search(title)
        if meta:
            return meta, ""
    except Exception as exc:
        crossref_error = f"Crossref: {exc}"
    else:
        crossref_error = "Crossref: no match"

    time.sleep(0.2)
    try:
        meta = openalex_search(title)
        if meta:
            return meta, crossref_error
    except Exception as exc:
        openalex_error = f"OpenAlex: {exc}"
    else:
        openalex_error = "OpenAlex: no match"

    time.sleep(0.2)
    try:
        meta = arxiv_search(title)
        if meta:
            return meta, f"{crossref_error}; {openalex_error}"
    except Exception as exc:
        return None, f"{crossref_error}; {openalex_error}; arXiv: {exc}"
    return None, f"{crossref_error}; {openalex_error}; arXiv: no match"


def main():
    if len(sys.argv) != 3:
        print("Usage: batch_endnote_from_titles.py <titles.txt> <output-dir>", file=sys.stderr)
        return 2

    titles_path = Path(sys.argv[1]).expanduser()
    output_dir = Path(sys.argv[2]).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    items = parse_titles(titles_path)
    manifest_path = output_dir / "manifest.csv"
    unmatched_path = output_dir / "unmatched_titles.txt"
    rows = []
    unmatched = []

    for pos, item in enumerate(items, start=1):
        index = item["index"]
        query_title = item["query_title"]
        print(f"[{pos}/{len(items)}] {query_title}", flush=True)
        meta, note = lookup(query_title)
        if not meta:
            rows.append(
                {
                    "index": index,
                    "status": "unmatched",
                    "query_title": query_title,
                    "matched_title": "",
                    "score": "",
                    "source": "",
                    "doi": "",
                    "year": "",
                    "file": "",
                    "note": note,
                }
            )
            unmatched.append(f"[{index}] {query_title}\t{note}")
            continue

        filename = safe_filename(index, meta["title"] or query_title)
        (output_dir / filename).write_text(to_enw(meta), encoding="utf-8")
        rows.append(
            {
                "index": index,
                "status": "ok",
                "query_title": query_title,
                "matched_title": meta.get("title", ""),
                "score": f"{meta.get('score', 0):.3f}",
                "source": meta.get("source", ""),
                "doi": meta.get("doi", ""),
                "year": meta.get("year", ""),
                "file": filename,
                "note": note,
            }
        )
        time.sleep(0.25)

    with manifest_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["index", "status", "query_title", "matched_title", "score", "source", "doi", "year", "file", "note"],
        )
        writer.writeheader()
        writer.writerows(rows)

    unmatched_path.write_text("\n".join(unmatched) + ("\n" if unmatched else ""), encoding="utf-8")
    ok = sum(1 for row in rows if row["status"] == "ok")
    print(f"Done: {ok}/{len(rows)} matched. Output: {output_dir}")
    if unmatched:
        print(f"Unmatched list: {unmatched_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
