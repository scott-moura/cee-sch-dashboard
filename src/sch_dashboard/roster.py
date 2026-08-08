from __future__ import annotations

import csv
import html
import re
from pathlib import Path

from .model import faculty_category, normalize_name


PROFILE = re.compile(r'title="([^"]+) Faculty Profile"')
SPAN = re.compile(r'<span class="(?:bold|italic)">(.*?)</span>', re.S)


def _plain(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_faculty_html(path: Path) -> list[dict[str, str]]:
    source = path.read_text(encoding="utf-8")
    matches = list(PROFILE.finditer(source))
    rows = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        segment = source[match.end():end]
        lines = [_plain(x) for x in SPAN.findall(segment)]
        lines = [x for x in lines if x and x != "Research Interests:"]
        title_text = " | ".join(lines)
        category = faculty_category(title_text)
        rows.append({
            "faculty_id": f"CEE-{index + 1:03d}",
            "canonical_name": html.unescape(match.group(1)),
            "source_name": html.unescape(match.group(1)),
            "title": title_text,
            "faculty_category": category,
            "cee_affiliated": "true",
            "fte_value": "1.0",
            "affiliation_source": "CEE current faculty webpage, 2026-08-08",
            "manual_override": "false",
            "notes": "POC assumes affiliation in all four terms",
        })
    return rows


def load_aliases(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {normalize_name(r["source_name"]): r["canonical_name"] for r in csv.DictReader(handle)}


def roster_lookup(rows: list[dict[str, str]], aliases: dict[str, str]) -> dict[str, dict[str, str]]:
    lookup = {normalize_name(r["canonical_name"]): r for r in rows}
    for source, canonical in aliases.items():
        if normalize_name(canonical) in lookup:
            lookup[source] = lookup[normalize_name(canonical)]
    return lookup

