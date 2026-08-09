from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
NEW_TERMS = {"Fall 2023", "Spring 2024"}


def priority(value: float) -> str:
    if value >= 300:
        return "HIGH"
    if value >= 100:
        return "MEDIUM"
    if value > 0:
        return "LOW"
    return "NO_CALCULABLE_SCH"


def meeting_signature(section: dict) -> str:
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    values = []
    for meeting in section.get("meetings") or []:
        days = "/".join(day for day, active in zip(day_names, meeting.get("days") or []) if active) or "TBA"
        start, end = meeting.get("startTime") or "TBA", meeting.get("endTime") or "TBA"
        location = meeting.get("location") or "TBA"
        values.append(f"{days} {start}-{end} @ {location}")
    return " ; ".join(values) or "TBA"


def read_section_meetings(path: Path, section_ids: set[str]) -> dict[tuple[str, str], str]:
    result = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            section_id = str(row.get("sectionId"))
            term = f"{row.get('semester')} {row.get('year')}"
            if term in NEW_TERMS and section_id in section_ids:
                result[(term, section_id)] = meeting_signature(row)
    return result


def build(sections_path: Path) -> dict:
    processed = ROOT / "data/processed"
    audit = ROOT / "data/audit"
    activities = pd.read_csv(processed / "instructional_activities.csv")
    offerings = pd.read_csv(processed / "course_offerings.csv")
    actionable = pd.read_csv(audit / "course_review_actionable.csv")
    faculty = pd.read_csv(processed / "faculty_roster.csv")
    semesters = pd.read_csv(processed / "faculty_semester.csv")

    instructor_review = actionable[
        actionable.term.isin(NEW_TERMS) & actionable.potential_course_sch.gt(0)
    ].copy()
    instructor_review = instructor_review.sort_values(
        ["potential_course_sch", "term", "course_codes", "person_to_resolve"],
        ascending=[False, True, True, True],
    )
    instructor_path = audit / "v1_2_instructor_credit_review.csv"
    instructor_review.to_csv(instructor_path, index=False)

    new_activities = activities[activities.term.isin(NEW_TERMS)].copy()
    grouping_candidates = new_activities[new_activities.potential_course_sch.gt(0)].groupby(
        ["term", "course_codes"], dropna=False
    ).filter(lambda rows: rows.activity_id.nunique() > 1)
    candidate_section_ids = {
        section_id
        for value in grouping_candidates.section_ids.fillna("")
        for section_id in str(value).split(" | ") if section_id
    }
    meeting_map = read_section_meetings(sections_path, candidate_section_ids)
    grouping_rows = []
    for (term, course_codes), rows in grouping_candidates.groupby(["term", "course_codes"]):
        rows = rows.sort_values("activity_id")
        total_potential = float(rows.potential_course_sch.sum())
        activity_descriptions = []
        for _, row in rows.iterrows():
            schedules = " || ".join(
                f"{section_id}: {meeting_map.get((term, section_id), 'TBA')}"
                for section_id in str(row.section_ids).split(" | ")
            )
            activity_descriptions.append(
                f"{row.activity_id}: sections {row.section_ids}; enrollment {row.actual_enrollment}; "
                f"potential SCH {row.potential_course_sch}; instructors {row.instructors}; meetings {schedules}"
            )
        grouping_rows.append({
            "term": term,
            "course_codes": course_codes,
            "activity_count": int(rows.activity_id.nunique()),
            "activity_ids": " | ".join(rows.activity_id),
            "combined_actual_enrollment": float(rows.actual_enrollment.sum()),
            "combined_potential_sch": total_potential,
            "impact_priority": priority(total_potential),
            "activity_details": " || ".join(activity_descriptions),
            "validation_question": "Do these rows represent separate offerings, or one shared instructional activity?",
            "decision": "",
            "allowed_decisions": "KEEP_SEPARATE | GROUP_AS_ONE_ACTIVITY | NEEDS_RESEARCH",
            "reviewer_notes": "",
        })
    grouping_review = pd.DataFrame(grouping_rows)
    grouping_resolutions = pd.read_csv(ROOT / "config/activity_grouping_resolutions.csv", keep_default_na=False)
    resolved_group_keys = set(zip(grouping_resolutions.term, grouping_resolutions.course_codes))
    if not grouping_review.empty:
        grouping_review = grouping_review[
            ~grouping_review.apply(lambda row: (row.term, row.course_codes) in resolved_group_keys, axis=1)
        ].sort_values(["combined_potential_sch", "term", "course_codes"], ascending=[False, True, True])
    grouping_path = audit / "v1_2_activity_grouping_review.csv"
    grouping_review.to_csv(grouping_path, index=False)

    primary = offerings[offerings.is_primary_section.astype(str).str.lower().eq("true")]
    unit_rows = []
    variable = new_activities[new_activities.exclusion_reason.eq("VARIABLE_UNITS")]
    for _, activity in variable.iterrows():
        rows = primary[primary.activity_id == activity.activity_id]
        if rows.empty or rows.units_min.isna().any() or rows.units_max.isna().any():
            continue
        if not (rows.units_min == rows.units_max).all() or rows.units_min.nunique() != 1:
            continue
        fixed_units = float(rows.units_min.iloc[0])
        calculable_sch = float(rows.latest_enrollment.fillna(0).sum() * fixed_units)
        if calculable_sch <= 0:
            continue
        unit_rows.append({
            "activity_id": activity.activity_id,
            "term": activity.term,
            "course_codes": activity.course_codes,
            "section_ids": activity.section_ids,
            "actual_enrollment": activity.actual_enrollment,
            "source_flag": "VARIABLE_UNITS",
            "common_section_units": fixed_units,
            "potential_sch_if_fixed": calculable_sch,
            "impact_priority": priority(calculable_sch),
            "instructors": activity.instructors,
            "validation_question": "Source flags variable units, but all linked sections have one common fixed min/max value. Keep excluded or approve a fixed-unit override?",
            "decision": "",
            "allowed_decisions": "KEEP_VARIABLE_EXCLUSION | APPROVE_FIXED_UNIT_OVERRIDE | NEEDS_RESEARCH",
            "reviewer_notes": "",
        })
    unit_review = pd.DataFrame(unit_rows, columns=[
        "activity_id", "term", "course_codes", "section_ids", "actual_enrollment",
        "source_flag", "common_section_units", "potential_sch_if_fixed", "impact_priority",
        "instructors", "validation_question", "decision", "allowed_decisions", "reviewer_notes",
    ])
    if not unit_review.empty:
        unit_review = unit_review.sort_values(
            ["potential_sch_if_fixed", "term", "course_codes"], ascending=[False, True, True]
        )
    unit_path = audit / "v1_2_unit_conflict_review.csv"
    unit_review.to_csv(unit_path, index=False)

    quality = new_activities[
        new_activities.exclusion_reason.isin(["MISSING_ENROLLMENT", "MISSING_UNITS"])
        & new_activities.data_quality_resolution.fillna("").eq("")
    ].copy()
    quality["impact_priority"] = quality.potential_course_sch.apply(priority)
    quality["validation_question"] = "Confirm exclusion or provide a reviewed source override."
    quality["decision"] = ""
    quality["allowed_decisions"] = "CONFIRM_EXCLUSION | SUPPLY_SOURCE_OVERRIDE | NEEDS_RESEARCH"
    quality["reviewer_notes"] = ""
    quality = quality[[
        "activity_id", "term", "course_codes", "section_ids", "actual_enrollment", "units_fixed",
        "potential_course_sch", "exclusion_reason", "instructors", "impact_priority",
        "validation_question", "decision", "allowed_decisions", "reviewer_notes",
    ]].sort_values(["potential_course_sch", "term", "course_codes"], ascending=[False, True, True])
    quality_path = audit / "v1_2_data_quality_review.csv"
    quality.to_csv(quality_path, index=False)

    new_semesters = semesters[semesters.term.isin(NEW_TERMS)]
    affiliation_approval = json.loads((ROOT / "config/faculty_affiliation_approval_v1.2.json").read_text())
    affiliation_rows = []
    for _, person in faculty[~faculty.faculty_id.astype(str).str.startswith("CEE-S")].iterrows():
        rows = new_semesters[new_semesters.faculty_id == person.faculty_id]
        fall = rows[rows.term == "Fall 2023"]
        spring = rows[rows.term == "Spring 2024"]
        provisional_sch = float(rows.attributed_sch.sum())
        affiliation_rows.append({
            "faculty_id": person.faculty_id,
            "faculty": person.canonical_name,
            "current_title": person.title,
            "faculty_category": person.faculty_category,
            "fall_2023_provisional_sch": float(fall.attributed_sch.sum()),
            "spring_2024_provisional_sch": float(spring.attributed_sch.sum()),
            "impact_priority": "HIGH" if provisional_sch > 0 else "DENOMINATOR_ONLY",
            "affiliation_decision": affiliation_approval["decision"],
            "allowed_decisions": "AFFILIATED_BOTH | FALL_ONLY | SPRING_ONLY | NEITHER | NEEDS_RESEARCH",
            "reviewer_notes": affiliation_approval["notes"],
        })
    affiliation_review = pd.DataFrame(affiliation_rows).sort_values(
        ["impact_priority", "faculty"], ascending=[True, True],
        key=lambda column: column.map({"HIGH": 0, "DENOMINATOR_ONLY": 1}) if column.name == "impact_priority" else column,
    )
    affiliation_path = audit / "v1_2_faculty_affiliation_review.csv"
    affiliation_review.to_csv(affiliation_path, index=False)

    pending_affiliations = int(affiliation_review.affiliation_decision.eq("").sum())
    deployment_ready = not any([
        len(instructor_review), len(grouping_review), len(unit_review), len(quality), pending_affiliations,
    ])
    summary = {
        "version": "1.2-audit",
        "new_terms": sorted(NEW_TERMS),
        "deployment_ready": deployment_ready,
        "new_term_activities": int(len(new_activities)),
        "new_term_attributed_sch": float(new_semesters.attributed_sch.sum()),
        "review_counts": {
            "instructor_credit_rows": int(len(instructor_review)),
            "instructor_credit_activities": int(instructor_review.activity_id.nunique()),
            "activity_grouping_rows": int(len(grouping_review)),
            "unit_conflict_rows": int(len(unit_review)),
            "data_quality_rows": int(len(quality)),
            "faculty_affiliation_rows": int(len(affiliation_review)),
            "faculty_affiliation_pending_rows": pending_affiliations,
        },
        "gate_reason": "" if deployment_ready else "v1.2 is provisional until all delta audit decisions are reviewed and persisted in configuration.",
    }
    (audit / "v1_2_audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    validation_path = audit / "validation_report.json"
    validation = json.loads(validation_path.read_text())
    # Preserve the calculation result across repeated gated audit runs. Once a gate has
    # set `passed` false, that combined value must not overwrite the underlying result.
    validation["calculation_passed"] = validation.get("calculation_passed", validation["passed"])
    validation["checks"]["v1_2_manual_audits_complete"] = deployment_ready
    validation["deployment_ready"] = deployment_ready
    validation["passed"] = validation["calculation_passed"] and deployment_ready
    validation["deployment_gate_reason"] = summary["gate_reason"]
    validation_path.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    return summary


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sections", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.sections), indent=2))


if __name__ == "__main__":
    cli()
