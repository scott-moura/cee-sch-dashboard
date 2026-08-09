from sch_dashboard.model import academic_year_fte, calculate_course_sch, catalog_number, faculty_category, latest_enrollment, observation_is_early, split_credit
from pathlib import Path

import pandas as pd

from sch_dashboard.pipeline import activity_key, faculty_classification_digest, load_instructor_resolutions, load_manual_validation_approvals
from sch_dashboard.dashboard_data import aggregate_courses, aggregate_department, aggregate_faculty


def test_catalog_number_handles_prefixes_and_suffixes():
    assert catalog_number("C106") == 106
    assert catalog_number("H194") == 194
    assert catalog_number("100A") == 100


def test_variable_history_uses_latest_timestamp():
    history = [
        {"endTime": {"$date": "2025-01-01T00:00:00Z"}, "enrolledCount": 10},
        {"endTime": {"$date": "2025-02-01T00:00:00Z"}, "enrolledCount": 12},
    ]
    assert latest_enrollment(history) == (12, "2025-02-01T00:00:00Z")


def test_team_teaching_splits_sch_and_enrollment():
    rows = split_credit(273, 91, ["A", "B", "A"])
    assert len(rows) == 2
    assert rows[0]["attributed_sch"] == 136.5
    assert rows[0]["attributed_enrollment"] == 45.5
    assert sum(x["attributed_sch"] for x in rows) == 273


def test_title_categories():
    assert faculty_category("Assistant Teaching Professor") == "REGULAR"
    assert faculty_category("Distinguished Professor") == "REGULAR"
    assert faculty_category("Professor of the Graduate School") == "NON_REGULAR"
    assert faculty_category("Senior Continuing Lecturer") == "NON_REGULAR"


def test_early_observation_flag():
    assert observation_is_early("2024-10-13T12:00:00Z", "2024-12-20")
    assert not observation_is_early("2025-12-20T00:00:00Z", "2025-12-19")


def test_variable_units_are_excluded():
    assert calculate_course_sch(10, 1, 4) == (0.0, "VARIABLE_UNITS")
    assert calculate_course_sch(10, 3, 3) == (30, "")


def test_crosslist_sections_share_activity_key():
    first = {"termId": "1", "sessionId": "1", "sectionId": "10", "subject": "CIVENG", "courseNumber": "C30", "number": "001", "combinedSections": [10, 20]}
    second = {"termId": "1", "sessionId": "1", "sectionId": "20", "subject": "MECENG", "courseNumber": "C85", "number": "001", "combinedSections": [20, 10]}
    assert activity_key(first, {}) == activity_key(second, {})


def test_academic_year_fte_averages_faculty_semesters():
    assert academic_year_fte(20) == 10
    assert academic_year_fte(1) == 0.5


def test_reviewed_instructor_resolutions_are_persisted():
    path = Path(__file__).resolve().parents[1] / "config/instructor_resolutions.csv"
    decisions = load_instructor_resolutions(path)
    assert len(decisions) == 41
    assert list(decisions.values()).count("EXCLUDE_GSI_TA") == 27
    assert list(decisions.values()).count("EXCLUDE_NOT_CEE_AFFILIATED") == 10
    assert list(decisions.values()).count("INCLUDE_NON_CEE_CO_INSTRUCTOR") == 4


def test_faculty_classification_approval_is_locked():
    from sch_dashboard.roster import parse_faculty_html
    root = Path(__file__).resolve().parents[1]
    roster = parse_faculty_html(root / "data/raw/cee/faculty-20260808.html")
    assert faculty_classification_digest(roster) == "34a5fead131fe8af0eb5c8673bae4dcb4b729fa4bbcf0943c3626184787c5fbe"


def test_evan_variano_schedule_name_resolves_to_roster():
    from sch_dashboard.roster import load_aliases, parse_faculty_html, roster_lookup
    from sch_dashboard.model import normalize_name
    root = Path(__file__).resolve().parents[1]
    roster = parse_faculty_html(root / "data/raw/cee/faculty-20260808.html")
    lookup = roster_lookup(roster, load_aliases(root / "config/faculty_aliases.csv"))
    assert lookup[normalize_name("Evan Variano")]["canonical_name"] == "Evan A. Variano"


def test_manual_edge_case_approvals_are_persisted():
    path = Path(__file__).resolve().parents[1] / "config/manual_validation_approval.csv"
    approvals = load_manual_validation_approvals(path)
    assert len(approvals) == 8
    assert list(row["review_status"] for row in approvals.values()).count("APPROVED") == 7
    assert approvals[("NON_CEE_CO_INSTRUCTOR", "NOT_OBSERVED")]["review_status"] == "N/A"


def test_dashboard_combines_selected_academic_years():
    root = Path(__file__).resolve().parents[1]
    department = pd.read_csv(root / "data/processed/department_academic_year.csv")
    faculty = pd.read_csv(root / "data/processed/faculty_academic_year.csv")
    years = ["2023-24", "2024-25", "2025-26"]
    totals = aggregate_department(department, years)
    assert totals["total_attributed_sch"] == 34_214
    assert totals["all_faculty_annual_fte"] == 205.5
    assert totals["sch_per_fte_all"] == 34_214 / 205.5
    ranking = aggregate_faculty(faculty, years, ["REGULAR", "NON_REGULAR"])
    assert len(ranking) == 76
    assert ranking.attributed_sch.sum() == 34_214


def test_course_leaderboard_groups_repeated_offerings_and_conserves_sch():
    root = Path(__file__).resolve().parents[1]
    activities = pd.read_csv(root / "data/processed/instructional_activities.csv")
    courses = aggregate_courses(activities, ["2024-25", "2025-26"])
    engin_7 = courses[courses.course_codes == "ENGIN 7"].iloc[0]
    assert engin_7.offerings == 2
    assert engin_7.sch_per_offering == engin_7.total_sch / 2
    included = activities[
        activities.academic_year.isin(["2024-25", "2025-26"])
        & ~activities.excluded_from_sch.astype(str).str.lower().eq("true")
    ]
    assert courses.total_sch.sum() == included.course_sch.sum()


def test_reviewed_non_regular_instructor_is_included_with_term_specific_fte():
    root = Path(__file__).resolve().parents[1]
    activities = pd.read_csv(root / "data/processed/instructional_activities.csv")
    fall_2024 = activities[
        (activities.term == "Fall 2024") & (activities.course_codes == "CIVENG 100")
    ].iloc[0]
    assert pd.isna(fall_2024.exclusion_reason)
    assert fall_2024.potential_course_sch == 480
    assert fall_2024.course_sch == 480
    semester = pd.read_csv(root / "data/processed/faculty_semester.csv")
    mallory = semester[semester.faculty == "Mallory Barkdull"]
    assert mallory.term.tolist() == ["Fall 2024"]
    assert mallory.attributed_sch.iloc[0] == 480


def test_non_cee_co_instructor_remains_in_divisor_without_cee_fte():
    root = Path(__file__).resolve().parents[1]
    attributions = pd.read_csv(root / "data/processed/instructor_attributions.csv")
    rows = attributions[attributions.activity_id == "X-2252-25588-27983"]
    assert set(rows.faculty) == {"David L. Sedlak", "Whendee Silver"}
    assert set(rows.teaching_credit_fraction) == {0.5}
    assert set(rows.attributed_sch) == {184.0}
    whendee = rows[rows.faculty == "Whendee Silver"].iloc[0]
    assert not whendee.cee_affiliated
    faculty = pd.read_csv(root / "data/processed/faculty_roster.csv")
    assert "Whendee Silver" not in set(faculty.canonical_name)


def test_reviewed_room_share_uses_section_specific_fixed_units():
    root = Path(__file__).resolve().parents[1]
    activities = pd.read_csv(root / "data/processed/instructional_activities.csv")
    row = activities[activities.activity_id == "X-2262-15882-34509"].iloc[0]
    assert row.course_codes == "CIVENG 153 | CYPLAN 190"
    assert row.actual_enrollment == 51
    assert row.units_fixed == 3
    assert row.course_sch == 153
    assert row.fixed_unit_override
    attributions = pd.read_csv(root / "data/processed/instructor_attributions.csv")
    credit = attributions[attributions.activity_id == row.activity_id].iloc[0]
    assert credit.faculty == "Marta Gonzalez"
    assert credit.attributed_sch == 153


def test_civeng_190_is_explicitly_excluded_by_course_policy():
    root = Path(__file__).resolve().parents[1]
    activities = pd.read_csv(root / "data/processed/instructional_activities.csv")
    rows = activities[activities.course_codes == "CIVENG 190"]
    assert len(rows) == 12
    assert set(rows.exclusion_reason) == {"COURSE_POLICY_EXCLUSION"}
    assert rows.course_policy_exclusion.all()
    assert rows.course_sch.sum() == 0


def test_98_and_198_are_explicitly_excluded_by_course_policy():
    root = Path(__file__).resolve().parents[1]
    activities = pd.read_csv(root / "data/processed/instructional_activities.csv")
    excluded_codes = {"CIVENG 98", "CIVENG 198", "ENGIN 98", "ENGIN 198"}
    rows = activities[
        activities.course_codes.str.split(" | ", regex=False).apply(
            lambda codes: bool(excluded_codes.intersection(codes))
        )
    ]
    assert len(rows) == 74
    assert set(rows.exclusion_reason) == {"COURSE_POLICY_EXCLUSION"}
    assert rows.course_policy_exclusion.all()
    assert rows.course_sch.sum() == 0


def test_v12_extension_manual_audit_gate_is_cleared():
    import json
    root = Path(__file__).resolve().parents[1]
    summary = json.loads((root / "data/audit/v1_2_audit_summary.json").read_text())
    assert summary["deployment_ready"]
    assert summary["new_term_attributed_sch"] == 10_590
    assert summary["review_counts"]["instructor_credit_rows"] == 0
    assert summary["review_counts"]["activity_grouping_rows"] == 0
    assert summary["review_counts"]["unit_conflict_rows"] == 0
    assert summary["review_counts"]["data_quality_rows"] == 0
    assert summary["review_counts"]["faculty_affiliation_rows"] == 65
