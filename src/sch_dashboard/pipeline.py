from __future__ import annotations

import argparse
import csv
import hashlib
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


def load_fixed_unit_overrides(path: Path) -> dict[str, dict[str, Any]]:
    result = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            activity_id = row["activity_id"]
            if activity_id in result:
                raise ValueError(f"Duplicate fixed-unit activity override: {activity_id}")
            result[activity_id] = {**row, "fixed_units": float(row["fixed_units"])}
    return result


def load_course_policy_exclusions(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    result = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (row["subject"], row["catalog_number"])
            if key in result:
                raise ValueError(f"Duplicate course policy exclusion: {key}")
            result[key] = row
    return result


def load_enrollment_overrides(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    result = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (row["term_id"], row["section_id"])
            if key in result:
                raise ValueError(f"Duplicate enrollment override: {key}")
            result[key] = {**row, "enrollment": int(row["enrollment"])}
    return result


def load_data_quality_resolutions(path: Path) -> dict[str, dict[str, str]]:
    allowed = {"CONFIRM_EXCLUSION"}
    result = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["decision"] not in allowed:
                raise ValueError(f"Invalid data-quality resolution: {row['decision']}")
            result[row["activity_id"]] = row
    return result


def load_instructor_resolutions(path: Path) -> dict[tuple[str, str], str]:
    allowed = {
        "INCLUDE_NON_CEE_CO_INSTRUCTOR", "ADD_CEE_NON_REGULAR", "EXCLUDE_GSI_TA",
        "EXCLUDE_NOT_CEE_AFFILIATED", "NEEDS_RESEARCH",
    }
    result = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            decision = row["decision"].strip()
            if decision not in allowed:
                raise ValueError(f"Invalid instructor decision: {decision}")
            result[(row["activity_id"], normalize_name(row["person"]))] = decision
    return result


def load_supplemental_faculty(path: Path) -> tuple[list[dict[str, str]], dict[str, set[str]]]:
    people: dict[str, dict[str, str]] = {}
    affiliated_terms: dict[str, set[str]] = defaultdict(set)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["faculty_category"] != "NON_REGULAR":
                raise ValueError(f"Supplemental faculty must be NON_REGULAR: {row['canonical_name']}")
            faculty_id = row["faculty_id"]
            person = {
                "faculty_id": faculty_id,
                "canonical_name": row["canonical_name"],
                "source_name": row["source_name"],
                "title": row["title"],
                "faculty_category": row["faculty_category"],
                "cee_affiliated": "true",
                "fte_value": "1.0",
                "affiliation_source": row["decision_source"],
                "manual_override": "true",
                "notes": row["notes"],
            }
            if faculty_id in people and people[faculty_id] != person:
                raise ValueError(f"Conflicting supplemental faculty rows: {faculty_id}")
            people[faculty_id] = person
            affiliated_terms[faculty_id].add(row["term_id"])
    return list(people.values()), affiliated_terms


def load_manual_validation_approvals(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    allowed = {"APPROVED", "N/A"}
    result = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            status = row["review_status"].strip()
            if status not in allowed:
                raise ValueError(f"Invalid manual validation status: {status}")
            result[(row["audit_category"], row["activity_id"])] = row
    return result


def faculty_classification_digest(roster: list[dict[str, str]]) -> str:
    payload = [
        {"faculty_id": r["faculty_id"], "canonical_name": r["canonical_name"], "faculty_category": r["faculty_category"]}
        for r in sorted(roster, key=lambda row: row["faculty_id"])
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def activity_key(section: dict[str, Any], overrides: dict[tuple[str, str, str, str], str]) -> str:
    override = overrides.get((section["termId"], section["subject"], section["courseNumber"], section["number"]))
    if override:
        return override
    combined = section.get("combinedSections") or []
    if combined:
        return f"X-{section['termId']}-" + "-".join(sorted(map(str, combined)))
    return f"S-{section['termId']}-{section['sessionId']}-{section['sectionId']}"


def build(args: argparse.Namespace) -> dict[str, int]:
    terms_config = Path(getattr(args, "terms_config", "config/terms.json"))
    if not terms_config.is_absolute():
        terms_config = ROOT / terms_config
    terms = json.loads(terms_config.read_text())
    term_by_id = {x["term_id"]: x for x in terms}
    term_keys = {(x["year"], x["semester"]) for x in terms}
    base_roster = parse_faculty_html(ROOT / "data/raw/cee/faculty-20260808.html")
    faculty_approval = json.loads((ROOT / "config/faculty_classification_approval.json").read_text())
    classification_approved = (
        len(base_roster) == faculty_approval["faculty_count"]
        and faculty_classification_digest(base_roster) == faculty_approval["classification_sha256"]
    )
    supplemental_roster, supplemental_terms = load_supplemental_faculty(
        ROOT / "config/supplemental_faculty_affiliations.csv"
    )
    roster = base_roster + supplemental_roster
    affiliated_terms = {person["faculty_id"]: set(term_by_id) for person in base_roster}
    affiliated_terms.update(supplemental_terms)
    aliases = load_aliases(ROOT / "config/faculty_aliases.csv")
    lookup = roster_lookup(roster, aliases)
    overrides = load_overrides(ROOT / "config/instructional_activity_overrides.csv")
    fixed_unit_overrides = load_fixed_unit_overrides(ROOT / "config/fixed_unit_activity_overrides.csv")
    course_policy_exclusions = load_course_policy_exclusions(ROOT / "config/course_policy_exclusions.csv")
    enrollment_overrides = load_enrollment_overrides(ROOT / "config/enrollment_overrides.csv")
    data_quality_resolutions = load_data_quality_resolutions(ROOT / "config/data_quality_resolutions.csv")
    resolutions = load_instructor_resolutions(ROOT / "config/instructor_resolutions.csv")
    manual_approvals = load_manual_validation_approvals(ROOT / "config/manual_validation_approval.csv")

    class_map = {}
    for row in read_jsonl(args.classes):
        if (row.get("year"), row.get("semester")) in term_keys:
            class_map[(row.get("termId"), row.get("sessionId"), row.get("subject"), row.get("courseNumber"), row.get("number"))] = row

    enrollment_map = {}
    for row in read_jsonl(args.enrollments):
        if (row.get("year"), row.get("semester")) in term_keys:
            enrollment_map[(row.get("termId"), row.get("sessionId"), row.get("sectionId"))] = latest_enrollment(row.get("history") or [])

    source_sections = []
    eligible_sections = []
    for row in read_jsonl(args.sections):
        if (row.get("year"), row.get("semester")) not in term_keys:
            continue
        number = catalog_number(row.get("courseNumber"))
        if number is None or number > 199:
            continue
        row = dict(row)
        source_sections.append(row)
        if not row.get("primary"):
            continue
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
    activity_by_course_key = {}
    for activity_id, sections in grouped.items():
        term_id = sections[0]["termId"]
        fixed_unit_override = fixed_unit_overrides.get(activity_id)
        policy_exclusion = next((
            course_policy_exclusions[(s["subject"], s["courseNumber"])]
            for s in sections if (s["subject"], s["courseNumber"]) in course_policy_exclusions
        ), None)
        group_study_policy_exclusion = bool(
            policy_exclusion
            and policy_exclusion["subject"] in {"CIVENG", "ENGIN"}
            and policy_exclusion["catalog_number"] in {"98", "198"}
        )
        data_quality_resolution = data_quality_resolutions.get(activity_id)
        listed_instructors = list(dict.fromkeys(name for s in sections for name in s["instructor_names"]))
        excluded_support = [
            name for name in listed_instructors
            if resolutions.get((activity_id, normalize_name(name))) == "EXCLUDE_GSI_TA"
        ]
        instructors = [name for name in listed_instructors if name not in excluded_support]
        cee_rows = []
        for name in instructors:
            person = lookup.get(normalize_name(name))
            if person and term_id not in affiliated_terms[person["faculty_id"]]:
                person = None
            cee_rows.append(person)
        # Every CIVENG activity remains visible even when no instructor matches
        # the approved roster. This prevents named lecturers and other potential
        # qualifying instructors from being silently discarded before audit.
        cee_course_candidate = any(s["subject"] == "CIVENG" for s in sections)
        if not any(cee_rows) and not cee_course_candidate:
            continue
        term = term_by_id[term_id]
        for section in sections:
            activity_by_course_key[(section["termId"], section["sessionId"], section["courseId"])] = activity_id
        units_values = []
        variable = False
        total_enrollment = 0
        observation_dates = []
        missing_enrollment = False
        applied_enrollment_overrides = []
        for s in sections:
            cls = class_map.get((s["termId"], s["sessionId"], s["subject"], s["courseNumber"], s["number"]))
            unit = (cls or {}).get("allowedUnits") or {}
            umin, umax = unit.get("minimum"), unit.get("maximum")
            if umin is not None and umax is not None:
                units_values.append((float(umin), float(umax)))
            if fixed_unit_override:
                expected_units = fixed_unit_override["fixed_units"]
                if umin is None or umax is None or float(umin) != expected_units or float(umax) != expected_units:
                    raise ValueError(
                        f"Fixed-unit override no longer matches source units for {activity_id}: "
                        f"{s['subject']} {s['courseNumber']} {s['number']} has {umin}-{umax}"
                    )
            elif fixed_units_flag(s) != "F" or (umin is not None and umax is not None and umin != umax):
                variable = True
            count, observed = enrollment_map.get((s["termId"], s["sessionId"], s["sectionId"]), (None, None))
            enrollment_override = enrollment_overrides.get((s["termId"], str(s["sectionId"])))
            if enrollment_override:
                count = enrollment_override["enrollment"]
                observed = enrollment_override["observation_date"] or observed
                applied_enrollment_overrides.append(enrollment_override)
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
                "is_variable_units": False if fixed_unit_override else fixed_units_flag(s) != "F" or umin != umax,
                "units_min": umin, "units_max": umax,
                "latest_enrollment": count, "enrollment_observation_date": observed,
                "enrollment_override": bool(enrollment_override),
                "enrollment_override_source": enrollment_override["decision_source"] if enrollment_override else "",
                "section_sch": 0.0 if (variable and not fixed_unit_override) or count is None or umin is None or umax is None or umin != umax else count * float(umin),
                "source_course_id": s.get("courseId"), "source_class_id": s.get("sectionId"),
            })
        fixed_values = {x[0] for x in units_values if x[0] == x[1]}
        units_fixed = fixed_unit_override["fixed_units"] if fixed_unit_override else (
            next(iter(fixed_values)) if len(fixed_values) == 1 and not variable else None
        )
        unresolved_instructors = [
            name for name, person in zip(instructors, cee_rows)
            if person is None and resolutions.get((activity_id, normalize_name(name)))
            not in {"INCLUDE_NON_CEE_CO_INSTRUCTOR", "ADD_CEE_NON_REGULAR", "EXCLUDE_NOT_CEE_AFFILIATED"}
        ]
        no_cee_instructor = bool(instructors) and not any(cee_rows)
        excluded = (
            bool(policy_exclusion) or variable or units_fixed is None or missing_enrollment or not instructors
            or bool(unresolved_instructors) or no_cee_instructor
        )
        reason = policy_exclusion["exclusion_reason"] if policy_exclusion else ("VARIABLE_UNITS" if variable else (
            "MISSING_UNITS" if units_fixed is None else (
                "MISSING_ENROLLMENT" if missing_enrollment else (
                    "UNRESOLVED_INSTRUCTOR" if not instructors or unresolved_instructors else (
                        "NO_CEE_AFFILIATED_INSTRUCTOR" if no_cee_instructor else ""
                    )
                )
            )
        ))
        potential_course_sch = total_enrollment * units_fixed if units_fixed is not None and not missing_enrollment else 0.0
        course_sch = 0.0 if excluded else potential_course_sch
        latest_date = max(observation_dates) if observation_dates else None
        early = observation_is_early(latest_date, term["end_date"])
        staff = not instructors
        non_roster = unresolved_instructors
        unresolved_data = reason in {"MISSING_UNITS", "MISSING_ENROLLMENT", "UNRESOLVED_INSTRUCTOR"}
        manual = False if policy_exclusion or data_quality_resolution else staff or bool(non_roster) or unresolved_data
        notable = manual or len(sections) > 1 or early or excluded or bool(excluded_support)
        activity = {
            "activity_id": activity_id, "term_id": term_id, "term": f"{term['semester']} {term['year']}",
            "academic_year": term["academic_year"], "course_codes": " | ".join(sorted({f"{s['subject']} {s['courseNumber']}" for s in sections})),
            "section_ids": " | ".join(s["sectionId"] for s in sections), "section_count": len(sections),
            "actual_enrollment": total_enrollment, "units_fixed": units_fixed,
            "potential_course_sch": potential_course_sch, "course_sch": course_sch,
            "all_listed_instructors": " | ".join(listed_instructors) if listed_instructors else "Staff/Unknown",
            "instructors": " | ".join(instructors) if instructors else "Staff/Unknown",
            "excluded_support_persons": " | ".join(excluded_support),
            "qualifying_instructor_count": len(instructors), "excluded_from_sch": excluded,
            "exclusion_reason": reason, "enrollment_observation_date": latest_date,
            "early_enrollment_observation": early, "manual_review_flag": manual,
            "fixed_unit_override": bool(fixed_unit_override),
            "fixed_unit_override_reason": fixed_unit_override["reason"] if fixed_unit_override else "",
            "course_policy_exclusion": bool(policy_exclusion),
            "course_policy_exclusion_notes": policy_exclusion["notes"] if policy_exclusion else "",
            "group_study_policy_exclusion": group_study_policy_exclusion,
            "enrollment_override_applied": bool(applied_enrollment_overrides),
            "enrollment_override_notes": " | ".join(x["notes"] for x in applied_enrollment_overrides),
            "data_quality_resolution": data_quality_resolution["decision"] if data_quality_resolution else "",
        }
        activities.append(activity)
        if notable:
            status = "PENDING" if manual else (
                "APPROVED_OVERRIDE" if activity_id.startswith("OVR-") or excluded_support or fixed_unit_override or policy_exclusion or applied_enrollment_overrides or data_quality_resolution
                else "APPROVED_RULE"
            )
            course_audit.append({**activity, "audit_status": status, "review_reasons": " | ".join(x for x in [
                "STAFF_OR_UNKNOWN" if staff else "", "NON_ROSTER_CO_INSTRUCTOR" if non_roster else "",
                "EXCLUDED_GSI_TA" if excluded_support else "", "GROUPED_ACTIVITY" if len(sections) > 1 else "",
                "FIXED_UNIT_OVERRIDE" if fixed_unit_override else "",
                "COURSE_POLICY_EXCLUSION" if policy_exclusion else "",
                "ENROLLMENT_OVERRIDE" if applied_enrollment_overrides else "",
                "DATA_QUALITY_RESOLUTION" if data_quality_resolution else "",
                "EARLY_ENROLLMENT_OBSERVATION" if early else "", reason,
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

    # Preserve linked secondary sections for auditability while assigning them
    # zero SCH. Their credit is already represented by the primary activity.
    for s in source_sections:
        if s.get("primary"):
            continue
        activity_id = activity_by_course_key.get((s["termId"], s["sessionId"], s["courseId"]))
        if not activity_id:
            continue
        term = term_by_id[s["termId"]]
        cls = class_map.get((s["termId"], s["sessionId"], s["subject"], s["courseNumber"], s["number"]))
        unit = (cls or {}).get("allowedUnits") or {}
        count, observed = enrollment_map.get((s["termId"], s["sessionId"], s["sectionId"]), (None, None))
        offerings.append({
            "activity_id": activity_id, "term": f"{term['semester']} {term['year']}",
            "academic_year": term["academic_year"], "subject": s["subject"],
            "catalog_number": s["courseNumber"], "section_number": s["number"],
            "section_id": s["sectionId"], "component": s.get("component"),
            "instruction_mode": s.get("instructionMode"), "is_primary_section": False,
            "is_variable_units": fixed_units_flag(s) != "F", "units_min": unit.get("minimum"),
            "units_max": unit.get("maximum"), "latest_enrollment": count,
            "enrollment_observation_date": observed, "section_sch": 0.0,
            "source_course_id": s.get("courseId"), "source_class_id": s.get("sectionId"),
        })

    # Complete zero-SCH faculty/term rows before annual aggregation.
    attr_index = defaultdict(list)
    for row in attributions:
        if row["cee_affiliated"]:
            attr_index[(row["faculty_id"], row["term"])].append(row)
    faculty_semester = []
    for person in roster:
        for term in terms:
            if term["term_id"] not in affiliated_terms[person["faculty_id"]]:
                continue
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
            "excluded_course_policy_activities": sum(1 for x in activities if x["academic_year"] == ay and x["exclusion_reason"] == "COURSE_POLICY_EXCLUSION"),
            "excluded_civeng_190_policy_activities": sum(
                1 for x in activities
                if x["academic_year"] == ay and "CIVENG 190" in x["course_codes"].split(" | ")
            ),
            "excluded_98_198_policy_activities": sum(1 for x in activities if x["academic_year"] == ay and x["group_study_policy_exclusion"]),
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
    actionable = []
    for row in course_audit:
        if row["audit_status"] != "PENDING":
            continue
        for instructor in (x for x in row["non_roster_instructors"].split(" | ") if x):
            actionable.append({
                "activity_id": row["activity_id"], "term": row["term"], "course_codes": row["course_codes"],
                "section_ids": row["section_ids"], "actual_enrollment": row["actual_enrollment"],
                "units_fixed": row["units_fixed"], "potential_course_sch": row["potential_course_sch"],
                "course_sch": row["course_sch"],
                "impact_priority": "HIGH" if row["potential_course_sch"] >= 300 else (
                    "MEDIUM" if row["potential_course_sch"] >= 100 else (
                        "LOW" if row["potential_course_sch"] > 0 else "NO_V1_SCH"
                    )
                ),
                "current_exclusion_reason": row["exclusion_reason"],
                "all_listed_instructors": row["instructors"], "person_to_resolve": instructor,
                "decision": "", "allowed_decisions": "ADD_FACULTY_ALIAS | ADD_CEE_NON_REGULAR | INCLUDE_NON_CEE_CO_INSTRUCTOR | EXCLUDE_GSI_TA | EXCLUDE_NOT_CEE_AFFILIATED | NEEDS_RESEARCH",
                "reviewer_notes": "",
            })
    actionable.sort(key=lambda row: (-float(row["potential_course_sch"]), row["term"], row["course_codes"], row["person_to_resolve"]))
    actionable_fields = list(actionable[0]) if actionable else [
        "activity_id", "term", "course_codes", "section_ids", "actual_enrollment", "units_fixed",
        "potential_course_sch", "course_sch", "impact_priority", "current_exclusion_reason",
        "all_listed_instructors", "person_to_resolve", "decision", "allowed_decisions", "reviewer_notes",
    ]
    write_csv(audit / "course_review_actionable.csv", actionable, actionable_fields)
    write_csv(
        audit / "course_review_actionable_sch.csv",
        [row for row in actionable if row["potential_course_sch"] > 0],
        actionable_fields,
    )
    activity_index = {row["activity_id"]: row for row in activities}
    secondary_counts = defaultdict(int)
    for row in offerings:
        if not row["is_primary_section"]:
            secondary_counts[row["activity_id"]] += 1
    sample_specs = [
        ("LARGE_LECTURE_AND_LINKED_SECTIONS", "S-2258-1-29115", "Confirm 432 × 4 = 1,728 SCH and all 16 secondary sections contribute zero."),
        ("SMALL_UNDERGRADUATE_COURSE", "S-2252-1-15372", "Confirm 1 × 3 = 3 SCH using the latest available observation."),
        ("TEAM_TAUGHT_COURSE", "X-2248-29286-33989", "Confirm two qualifying faculty split 72 SCH equally (36 each)."),
        ("CROSS_LISTED_COURSE", "X-2258-25290-28631-29871", "Confirm three listings form one 99-student activity and 396 SCH."),
        ("VARIABLE_UNIT_EXCLUSION", "S-2248-1-34658", "Confirm CIVENG 199 is retained but contributes zero Version 1 SCH."),
        ("NON_REGULAR_FACULTY", "S-2248-1-28421", "Confirm Jasenka Rakas is NON_REGULAR and receives 111 SCH."),
        ("OUTSIDE_CIVENG_SUBJECT", "S-2262-1-21249", "Confirm ARCH 140 taught by CEE faculty contributes 620 SCH."),
    ]
    manual_sample = []
    for category, activity_id, question in sample_specs:
        row = activity_index[activity_id]
        approval = manual_approvals.get((category, activity_id), {})
        manual_sample.append({
            "audit_category": category, "activity_id": activity_id, "term": row["term"],
            "course_codes": row["course_codes"], "actual_enrollment": row["actual_enrollment"],
            "units_fixed": row["units_fixed"], "course_sch": row["course_sch"],
            "qualifying_instructors": row["instructors"],
            "qualifying_instructor_count": row["qualifying_instructor_count"],
            "expected_fraction_each": 1 / row["qualifying_instructor_count"] if row["qualifying_instructor_count"] else "",
            "expected_attributed_sch_each": row["course_sch"] / row["qualifying_instructor_count"] if row["qualifying_instructor_count"] else "",
            "linked_secondary_sections": secondary_counts[activity_id],
            "enrollment_observation_date": row["enrollment_observation_date"],
            "validation_question": question, "review_status": approval.get("review_status", ""),
            "reviewer_notes": approval.get("notes", ""),
        })
    non_cee_approval = manual_approvals.get(("NON_CEE_CO_INSTRUCTOR", "NOT_OBSERVED"), {})
    manual_sample.append({
        "audit_category": "NON_CEE_CO_INSTRUCTOR", "activity_id": "NOT_OBSERVED", "term": "",
        "course_codes": "", "actual_enrollment": "", "units_fixed": "", "course_sch": "",
        "qualifying_instructors": "", "qualifying_instructor_count": "", "expected_fraction_each": "",
        "expected_attributed_sch_each": "", "linked_secondary_sections": "",
        "enrollment_observation_date": "", "validation_question": "No qualifying non-CEE co-instructor remained after review; all 14 non-roster names were classified as GSIs/TAs.",
        "review_status": non_cee_approval.get("review_status", ""),
        "reviewer_notes": non_cee_approval.get("notes", ""),
    })
    manual_validation_approved = all(row["review_status"] in {"APPROVED", "N/A"} for row in manual_sample)
    write_csv(audit / "manual_validation_sample.csv", manual_sample)
    write_csv(audit / "faculty_review.csv", [
        {**r, "audit_status": "APPROVED" if classification_approved else "PENDING",
         "reviewer_category": r["faculty_category"] if classification_approved else "",
         "reviewer_notes": "Approved classification set" if classification_approved else ""}
        for r in roster
    ])
    from .validate import validate_outputs
    validation = validate_outputs(processed)
    validation["checks"]["faculty_classifications_approved"] = classification_approved
    validation["checks"]["manual_edge_cases_approved"] = manual_validation_approved
    validation["faculty_audit_approved"] = classification_approved
    validation["manual_validation_approved"] = manual_validation_approved
    validation["passed"] = validation["passed"] and classification_approved and manual_validation_approved
    (audit / "validation_report.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    try:
        import duckdb
        db = duckdb.connect(str(processed / "sch.duckdb"))
        for name in ("faculty_roster", "course_offerings", "instructional_activities", "instructor_attributions", "faculty_semester", "faculty_academic_year", "department_academic_year"):
            db.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_csv_auto(?)", [str(processed / f"{name}.csv")])
        db.close()
    except ImportError:
        pass
    return {"faculty": len(roster), "faculty_audit_approved": classification_approved,
            "manual_validation_approved": manual_validation_approved, "activities": len(activities),
            "attributions": len(attributions), "course_audits": len(course_audit),
            "validation_passed": validation["passed"]}


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sections", type=Path, required=True)
    parser.add_argument("--classes", type=Path, required=True)
    parser.add_argument("--enrollments", type=Path, required=True)
    parser.add_argument("--terms-config", type=Path, default=Path("config/terms.json"))
    args = parser.parse_args()
    print(json.dumps(build(args), indent=2))


if __name__ == "__main__":
    cli()
