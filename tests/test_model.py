from sch_dashboard.model import academic_year_fte, calculate_course_sch, catalog_number, faculty_category, latest_enrollment, observation_is_early, split_credit
from sch_dashboard.pipeline import activity_key


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
