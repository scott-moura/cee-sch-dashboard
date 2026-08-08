from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Any, Iterable


REGULAR_PHRASES = (
    "assistant teaching professor",
    "associate teaching professor",
    "teaching professor",
    "assistant professor",
    "associate professor",
    "distinguished professor",
    "chancellor's professor",
    "professor",
)
NON_REGULAR_PHRASES = (
    "professor of the graduate school",
    "adjunct professor",
    "professor in-residence",
    "visiting professor",
    "continuing lecturer",
    "lecturer",
    "emeritus",
)


def normalize_name(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def catalog_number(value: str | None) -> int | None:
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else None


def faculty_category(title: str) -> str:
    lowered = normalize_name(title)
    if any(normalize_name(x) in lowered for x in NON_REGULAR_PHRASES):
        return "NON_REGULAR"
    if any(normalize_name(x) in lowered for x in REGULAR_PHRASES):
        return "REGULAR"
    return "REVIEW"


def latest_enrollment(history: Iterable[dict[str, Any]]) -> tuple[int | None, str | None]:
    candidates = []
    for item in history or []:
        stamp = item.get("endTime") or item.get("startTime")
        if isinstance(stamp, dict):
            stamp = stamp.get("$date")
        if stamp:
            candidates.append((stamp, item.get("enrolledCount")))
    if not candidates:
        return None, None
    stamp, count = max(candidates, key=lambda pair: pair[0])
    return count, stamp


def observation_is_early(observed: str | None, term_end: str, days: int = 14) -> bool:
    if not observed:
        return True
    observed_date = datetime.fromisoformat(observed.replace("Z", "+00:00")).date()
    return (date.fromisoformat(term_end) - observed_date).days > days


def split_credit(course_sch: float, enrollment: float, instructors: list[str]) -> list[dict[str, float | str]]:
    unique = list(dict.fromkeys(x for x in instructors if x))
    if not unique:
        return []
    fraction = 1.0 / len(unique)
    return [
        {
            "instructor": name,
            "teaching_credit_fraction": fraction,
            "attributed_sch": course_sch * fraction,
            "attributed_enrollment": enrollment * fraction,
        }
        for name in unique
    ]


def calculate_course_sch(enrollment: float, units_min: float | None, units_max: float | None) -> tuple[float, str]:
    if units_min is None or units_max is None:
        return 0.0, "MISSING_UNITS"
    if units_min != units_max:
        return 0.0, "VARIABLE_UNITS"
    return enrollment * units_min, ""


def academic_year_fte(faculty_semesters: float) -> float:
    """Convert two-semester faculty-semester accounting to average annual FTE."""
    return faculty_semesters / 2.0
