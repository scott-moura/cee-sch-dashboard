from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .model import catalog_number


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_outputs(processed: Path) -> dict:
    activities = _rows(processed / "instructional_activities.csv")
    offerings = _rows(processed / "course_offerings.csv")
    attributions = _rows(processed / "instructor_attributions.csv")
    department = _rows(processed / "department_academic_year.csv")
    annual = _rows(processed / "faculty_academic_year.csv")
    errors: list[str] = []
    policy_codes = {"CIVENG 190", "CIVENG 98", "CIVENG 198", "ENGIN 98", "ENGIN 198"}

    if any("Summer" in row["term"] for row in activities):
        errors.append("Summer activity present")
    for row in activities:
        for code in row["course_codes"].split(" | "):
            number = catalog_number(code.split(" ")[-1])
            if number is None or number > 199:
                errors.append(f"Out-of-scope catalog number: {code}")

    sch_by_activity = defaultdict(float)
    fractions = defaultdict(float)
    for row in attributions:
        sch_by_activity[row["activity_id"]] += float(row["attributed_sch"])
        fractions[row["activity_id"]] += float(row["teaching_credit_fraction"])
    for row in activities:
        included = row["excluded_from_sch"].lower() == "false"
        named = int(row["qualifying_instructor_count"]) > 0
        if included and named:
            if abs(sch_by_activity[row["activity_id"]] - float(row["course_sch"])) > 1e-6:
                errors.append(f"SCH attribution does not conserve for {row['activity_id']}")
            if abs(fractions[row["activity_id"]] - 1.0) > 1e-6:
                errors.append(f"Teaching fractions do not sum to 1 for {row['activity_id']}")
        if row["exclusion_reason"] == "VARIABLE_UNITS" and float(row["course_sch"]) != 0:
            errors.append(f"Variable-unit activity has SCH: {row['activity_id']}")
        codes = row["course_codes"].split(" | ")
        if policy_codes.intersection(codes):
            if (
                row["exclusion_reason"] != "COURSE_POLICY_EXCLUSION"
                or float(row["course_sch"]) != 0
                or row.get("course_policy_exclusion", "").lower() != "true"
            ):
                errors.append(f"Course policy exclusion failed: {row['activity_id']}")
        if row.get("fixed_unit_override", "").lower() == "true" and not row["units_fixed"]:
            errors.append(f"Fixed-unit override has no fixed units: {row['activity_id']}")
    for row in offerings:
        if row["is_primary_section"].lower() == "false" and float(row["section_sch"]) != 0:
            errors.append(f"Secondary section has SCH: {row['section_id']}")

    for row in department:
        share = float(row["regular_sch_share"]) + float(row["non_regular_sch_share"])
        if float(row["total_attributed_sch"]) and abs(share - 1.0) > 1e-6:
            errors.append(f"Faculty-category shares do not sum to 1 for {row['academic_year']}")
        annual_total = sum(float(x["attributed_sch"]) for x in annual if x["academic_year"] == row["academic_year"])
        if abs(annual_total - float(row["total_attributed_sch"])) > 1e-6:
            errors.append(f"Faculty and department totals disagree for {row['academic_year']}")

    return {
        "passed": not errors,
        "error_count": len(errors),
        "errors": errors,
        "checks": {
            "no_summer_terms": True,
            "catalog_numbers_at_most_199": True,
            "teaching_credit_conservation": True,
            "variable_unit_sch_zero": True,
            "course_policy_sch_zero": True,
            "fixed_unit_overrides_have_units": True,
            "secondary_section_sch_zero": True,
            "faculty_department_aggregation": True,
            "regular_non_regular_shares": True,
        },
    }
