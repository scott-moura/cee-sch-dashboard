from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .model import academic_year_fte, catalog_number, latest_enrollment, normalize_name, observation_is_early, split_credit
from .roster import load_aliases, parse_faculty_html, roster_lookup

ROOT = Path(__file__).resolve().parents[2]


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def visible_instructors(section: dict[str, Any]) -> list[str]:
    names = []
    for meeting in section.get("meetings") or []:
        for instructor in meeting.get("instructors") or []:
            if not instructor.get("printInScheduleOfClasses"):
                continue
            name = " ".join(x for x in (instructor.get("givenName"), instructor.get("familyName")) if x)
            name = " ".join(name.split())
            if name and name not in names:
                names.append(name)
    return names


def fixed_units_flag(section: dict[str, Any]) -> str | None:
    for item in section.get("sectionAttributes") or []:
        if item.get("attribute", {}).get("code") == "VUOC":
            return item.get("value", {}).get("code")
    return None


def load_overrides(path: Path) -> dict[tuple[str, str, str, str], str]:
    result = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for number in row["section_numbers"].split("|"):
                result[(row["term_id"], row["subject"], row["catalog_number"], number)] = row["activity_id"]
    return result


def activity_key(section: dict[str, Any], overrides: dict[tuple[str, str, str, str], str]) -> str:
    override = overrides.get((section["termId"], section["subject"], section["courseNumber"], section["number"]))
    if override:
        return override
    combined = section.get("combinedSections") or []
    if combined:
        return f"X-{section['termId']}-" + "-".join(sorted(map(str, combined)))
    return f"S-{section['termId']}-{section['sessionId']}-{section['sectionId']}"


def build(args: argparse.Namespace) -> dict[str, int]:
    terms = json.loads((ROOT / "config/terms.json").read_text())
    term_by_id = {x["term_id"]: x for x in terms}
    term_keys = {(x["year"], x["semester"]) for x in terms}
    roster = parse_faculty_html(ROOT / "data/raw/cee/faculty-20260808.html")
    aliases = load_aliases(ROOT / "config/faculty_aliases.csv")
    lookup = roster_lookup(roster, aliases)
    overrides = load_overrides(ROOT / "config/instructional_activity_overrides.csv")

    class_map = {}
    for row in read_jsonl(args.classes):
        if (row.get("year"), row.get("semester")) in term_keys:
            class_map[(row.get("termId"), row.get("sessionId"), row.get("subject"), row.get("courseNumber"), row.get("number"))] = row

    enrollment_map = {}
    for row in read_jsonl(args.enrollments):
        if (row.get("year"), row.get("semester")) in term_keys:
            enrollment_map[(row.get("termId"), row.get("sessionId"), row.get("sectionId"))] = latest_enrollment(row.get("history") or [])

    eligible_sections = []
    for row in read_jsonl(args.sections):
        if (row.get("year"), row.get("semester")) not in term_keys or not row.get("primary"):
            continue
        number = catalog_number(row.get("courseNumber"))
        if number is None or number > 199:
            continue
        row = dict(row)
        row["instructor_names"] = visible_instructors(row)
        row["activity_id"] = activity_key(row, overrides)
        eligible_sections.append(row)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible_sections:
        grouped[row["activity_id"]].append(row)

    activities = []
    attributions = []
    course_audit = []
    offerings = []
    for activity_id, sections in grouped.items():
        instructors = list(dict.fromkeys(name for s in sections for name in s["instructor_names"]))
        cee_rows = [lookup.get(normalize_name(name)) for name in instructors]
        # A CIVENG activity with no named instructor remains in the audit queue
        # (CIVENG 176 in Fall 2025 is the current example). It cannot contribute
        # SCH until a qualifying instructor is resolved.
        staff_cee_candidate = not instructors and any(s["subject"] == "CIVENG" for s in sections)
        if not any(cee_rows) and not staff_cee_candidate:
            continue
        term_id = sections[0]["termId"]
        term = term_by_id[term_id]
        units_values = []
        variable = False
        total_enrollment = 0
        observation_dates = []
        missing_enrollment = False
        for s in sections:
            cls = class_map.get((s["termId"], s["sessionId"], s["subject"], s["courseNumber"], s["number"]))
            unit = (cls or {}).get("allowedUnits") or {}
            umin, umax = unit.get("minimum"), unit.get("maximum")
            if umin is not None and umax is not None:
                units_values.append((float(umin), float(umax)))
            if fixed_units_flag(s) != "F" or (umin is not None and umax is not None and umin != umax):
                variable = True
            count, observed = enrollment_map.get((s["termId"], s["sessionId"], s["sectionId"]), (None, None))
            if count is None:
                missing_enrollment = True
            else:
                total_enrollment += count
            if observed:
                observation_dates.append(observed)
            offerings.append({
                "activity_id": activity_id, "term": f"{term['semester']} {term['year']}",
                "academic_year": term["academic_year"], "subject": s["subject"],
                "catalog_number": s["courseNumber"], "section_number": s["number"],
                "section_id": s["sectionId"], "component": s.get("component"),
                "instruction_mode": s.get("instructionMode"), "is_primary_section": True,
                "is_variable_units": variable, "units_min": umin, "units_max": umax,
                "latest_enrollment": count, "enrollment_observation_date": observed,
                "source_course_id": s.get("courseId"), "source_class_id": s.get("sectionId"),
            })
        fixed_values = {x[0] for x in units_values if x[0] == x[1]}
        units_fixed = next(iter(fixed_values)) if len(fixed_values) == 1 and not variable else None
        excluded = variable or units_fixed is None or missing_enrollment or not instructors
        reason = "VARIABLE_UNITS" if variable else (
            "MISSING_UNITS" if units_fixed is None else (
                "MISSING_ENROLLMENT" if missing_enrollment else (
                    "UNRESOLVED_INSTRUCTOR" if not instructors else ""
                )
            )
        )
        course_sch = 0.0 if excluded else total_enrollment * units_fixed
        latest_date = max(observation_dates) if observation_dates else None
        early = observation_is_early(latest_date, term["end_date"])
        staff = not instructors
        non_roster = [name for name, person in zip(instructors, cee_rows) if person is None]
        unresolved_data = reason in {"MISSING_UNITS", "MISSING_ENROLLMENT", "UNRESOLVED_INSTRUCTOR"}
        manual = staff or bool(non_roster) or unresolved_data
        notable = manual or len(sections) > 1 or early or excluded
        activity = {
            "activity_id": activity_id, "term_id": term_id, "term": f"{term['semester']} {term['year']}",
            "academic_year": term["academic_year"], "course_codes": " | ".join(sorted({f"{s['subject']} {s['courseNumber']}" for s in sections})),
            "section_ids": " | ".join(s["sectionId"] for s in sections), "section_count": len(sections),
            "actual_enrollment": total_enrollment, "units_fixed": units_fixed, "course_sch": course_sch,
            "instructors": " | ".join(instructors) if instructors else "Staff/Unknown",
            "qualifying_instructor_count": len(instructors), "excluded_from_sch": excluded,
            "exclusion_reason": reason, "enrollment_observation_date": latest_date,
            "early_enrollment_observation": early, "manual_review_flag": manual,
        }
        activities.append(activity)
        if notable:
            status = "PENDING" if manual else ("APPROVED_OVERRIDE" if activity_id.startswith("OVR-") else "APPROVED_RULE")
            course_audit.append({**activity, "audit_status": status, "review_reasons": " | ".join(x for x in [
                "STAFF_OR_UNKNOWN" if staff else "", "NON_ROSTER_CO_INSTRUCTOR" if non_roster else "",
                "GROUPED_ACTIVITY" if len(sections) > 1 else "", "EARLY_ENROLLMENT_OBSERVATION" if early else "", reason,
            ] if x), "non_roster_instructors": " | ".join(non_roster), "reviewer_notes": ""})
        if not excluded and instructors:
            for credit in split_credit(course_sch, total_enrollment, instructors):
                person = lookup.get(normalize_name(str(credit["instructor"])))
                attributions.append({
                    "activity_id": activity_id, "term": activity["term"], "academic_year": term["academic_year"],
                    "faculty_id": person["faculty_id"] if person else "", "faculty": person["canonical_name"] if person else credit["instructor"],
                    "cee_affiliated": bool(person), "faculty_category": person["faculty_category"] if person else "NON_CEE",
                    "course_codes": activity["course_codes"], "actual_enrollment": total_enrollment,
                    "attributed_course_enrollments": credit["attributed_enrollment"],
                    "units_fixed": units_fixed, "course_sch": course_sch,
                    "teaching_credit_fraction": credit["teaching_credit_fraction"], "attributed_sch": credit["attributed_sch"],
                    "enrollment_observation_date": latest_date,
                })

    # Complete zero-SCH faculty/term rows before annual aggregation.
    attr_index = defaultdict(list)
    for row in attributions:
        if row["cee_affiliated"]:
            attr_index[(row["faculty_id"], row["term"])].append(row)
    faculty_semester = []
    for person in roster:
        for term in terms:
            label = f"{term['semester']} {term['year']}"
            rows = attr_index[(person["faculty_id"], label)]
            faculty_semester.append({
                "faculty_id": person["faculty_id"], "faculty": person["canonical_name"], "title": person["title"],
                "faculty_category": person["faculty_category"], "term": label, "academic_year": term["academic_year"],
                "fte": 1.0, "attributed_sch": sum(float(x["attributed_sch"]) for x in rows),
                "attributed_course_enrollments": sum(float(x["attributed_course_enrollments"]) for x in rows),
                "qualifying_primary_courses": len({x["activity_id"] for x in rows}),
            })
    annual = []
    for person in roster:
        for ay in sorted({x["academic_year"] for x in terms}):
            rows = [x for x in faculty_semester if x["faculty_id"] == person["faculty_id"] and x["academic_year"] == ay]
            annual.append({
                "academic_year": ay, "faculty_id": person["faculty_id"], "faculty": person["canonical_name"],
                "title": person["title"], "faculty_category": person["faculty_category"],
                "annual_fte": academic_year_fte(sum(x["fte"] for x in rows)),
                "attributed_sch": sum(x["attributed_sch"] for x in rows),
                "attributed_course_enrollments": sum(x["attributed_course_enrollments"] for x in rows),
                "qualifying_primary_courses": sum(x["qualifying_primary_courses"] for x in rows),
            })
    department = []
    for ay in sorted({x["academic_year"] for x in terms}):
        rows = [x for x in annual if x["academic_year"] == ay]
        total = sum(x["attributed_sch"] for x in rows)
        regular = sum(x["attributed_sch"] for x in rows if x["faculty_category"] == "REGULAR")
        nonregular = sum(x["attributed_sch"] for x in rows if x["faculty_category"] == "NON_REGULAR")
        all_fte = sum(x["annual_fte"] for x in rows)
        regular_fte = sum(x["annual_fte"] for x in rows if x["faculty_category"] == "REGULAR")
        department.append({
            "academic_year": ay, "total_attributed_sch": total, "regular_attributed_sch": regular,
            "non_regular_attributed_sch": nonregular, "regular_sch_share": regular / total if total else 0,
            "non_regular_sch_share": nonregular / total if total else 0,
            "all_faculty_annual_fte": all_fte, "regular_annual_fte": regular_fte,
            "sch_per_fte_all": total / all_fte if all_fte else 0,
            "sch_per_fte_regular_denominator": total / regular_fte if regular_fte else 0,
            "excluded_variable_unit_activities": sum(1 for x in activities if x["academic_year"] == ay and x["exclusion_reason"] == "VARIABLE_UNITS"),
        })

    processed = ROOT / "data/processed"; audit = ROOT / "data/audit"
    write_csv(processed / "faculty_roster.csv", roster)
    write_csv(processed / "course_offerings.csv", offerings)
    write_csv(processed / "instructional_activities.csv", activities)
    write_csv(processed / "instructor_attributions.csv", attributions)
    write_csv(processed / "faculty_semester.csv", faculty_semester)
    write_csv(processed / "faculty_academic_year.csv", annual)
    write_csv(processed / "department_academic_year.csv", department)
    write_csv(audit / "course_review.csv", course_audit)
    write_csv(audit / "course_review_pending.csv", [r for r in course_audit if r["audit_status"] == "PENDING"])
    write_csv(audit / "faculty_review.csv", [
        {**r, "audit_status": "PENDING", "reviewer_category": "", "reviewer_notes": ""}
        for r in roster
    ])
    from .validate import validate_outputs
    validation = validate_outputs(processed)
    (audit / "validation_report.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    try:
        import duckdb
        db = duckdb.connect(str(processed / "sch.duckdb"))
        for name in ("faculty_roster", "course_offerings", "instructional_activities", "instructor_attributions", "faculty_semester", "faculty_academic_year", "department_academic_year"):
            db.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_csv_auto(?)", [str(processed / f"{name}.csv")])
        db.close()
    except ImportError:
        pass
    return {"faculty": len(roster), "activities": len(activities), "attributions": len(attributions), "course_audits": len(course_audit), "validation_passed": validation["passed"]}


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sections", type=Path, required=True)
    parser.add_argument("--classes", type=Path, required=True)
    parser.add_argument("--enrollments", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args), indent=2))


if __name__ == "__main__":
    cli()
