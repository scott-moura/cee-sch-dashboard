import json
from pathlib import Path

import pandas as pd
import streamlit as st

from sch_dashboard.dashboard_data import aggregate_courses, aggregate_department, aggregate_faculty

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"

st.set_page_config(page_title="CEE SCH Dashboard", layout="wide")
st.title("CEE Undergraduate Student Credit Hours")
audit_summary_path = ROOT / "data/audit/v1_2_audit_summary.json"
audit_summary = json.loads(audit_summary_path.read_text()) if audit_summary_path.exists() else None
if audit_summary and not audit_summary["deployment_ready"]:
    st.caption("Provisional Version 1.2 audit build · Latest available public enrollment observations")
    st.error(audit_summary["gate_reason"])
else:
    st.caption("Validated Version 1.2 · Fall 2023–Spring 2026 · Latest available public enrollment observations")
st.warning("SCH is an instructional credit-hour diagnostic, not a measure of total faculty workload or performance. Variable-unit courses, all CIVENG 190 pilot sections, and all CIVENG/ENGIN 98 and 198 group-study activities are excluded.")

required = ["faculty_academic_year.csv", "department_academic_year.csv", "instructor_attributions.csv", "instructional_activities.csv"]
if not all((DATA / name).exists() for name in required):
    st.error("Processed data are missing. Run the pipeline described in README.md.")
    st.stop()

faculty = pd.read_csv(DATA / "faculty_academic_year.csv")
dept = pd.read_csv(DATA / "department_academic_year.csv")
attrib = pd.read_csv(DATA / "instructor_attributions.csv")
activities = pd.read_csv(DATA / "instructional_activities.csv")

available_years = sorted(faculty.academic_year.unique(), reverse=True)
academic_years = st.sidebar.multiselect("Academic years", available_years, default=available_years)
category = st.sidebar.multiselect(
    "Faculty category", ["REGULAR", "NON_REGULAR", "REVIEW"],
    default=["REGULAR", "NON_REGULAR", "REVIEW"],
)
if not academic_years:
    st.error("Select at least one academic year.")
    st.stop()

period_label = ", ".join(sorted(academic_years))
st.caption(f"Selected period: {period_label}. Totals and rankings combine all selected academic years.")

d = aggregate_department(dept, academic_years)
f = aggregate_faculty(faculty, academic_years, category)

cards = st.columns(4)
cards[0].metric("Total attributed SCH", f"{d['total_attributed_sch']:,.1f}")
cards[1].metric("Regular attributed SCH", f"{d['regular_attributed_sch']:,.1f}")
cards[2].metric("Non-regular attributed SCH", f"{d['non_regular_attributed_sch']:,.1f}")
cards[3].metric("Variable-unit activities excluded", f"{int(d['excluded_variable_unit_activities']):,}")
cards = st.columns(4)
cards[0].metric("Regular SCH share", f"{d['regular_sch_share']:.1%}")
cards[1].metric("Non-regular SCH share", f"{d['non_regular_sch_share']:.1%}")
cards[2].metric("SCH/FTE-year — all faculty", f"{d['sch_per_fte_all']:,.1f}")
cards[3].metric("SCH/FTE-year — regular denominator", f"{d['sch_per_fte_regular_denominator']:,.1f}")

st.subheader("Faculty leaderboard")
f.insert(0, "Rank", range(1, len(f) + 1))
f["department_sch_share"] = f.attributed_sch / d["total_attributed_sch"] if d["total_attributed_sch"] else 0
st.dataframe(
    f[["Rank", "faculty", "title", "faculty_category", "selected_period_fte", "attributed_sch",
       "qualifying_offerings", "attributed_course_enrollments", "department_sch_share"]],
    width="stretch", hide_index=True,
    column_config={
        "selected_period_fte": "Selected-period FTE-years",
        "qualifying_offerings": "Qualifying offerings",
        "department_sch_share": st.column_config.NumberColumn("Department SCH share", format="percent"),
    },
)

st.subheader("Faculty drill-down")
if f.empty:
    st.info("No faculty match the selected categories.")
    selected_faculty = None
else:
    selected_faculty = st.selectbox("Faculty member", f.faculty.tolist())
    detail = attrib[attrib.academic_year.isin(academic_years) & (attrib.faculty == selected_faculty)].copy()
    terms = ["All"] + sorted(detail.term.dropna().unique().tolist())
    term_filter = st.selectbox("Semester", terms)
    if term_filter != "All":
        detail = detail[detail.term == term_filter]
    subjects = sorted({code.split(" ")[0] for value in detail.course_codes.dropna() for code in value.split(" | ")})
    subject_filter = st.selectbox("Subject/course", ["All"] + subjects)
    if subject_filter != "All":
        detail = detail[detail.course_codes.str.contains(subject_filter, regex=False)]
    st.dataframe(
        detail[["academic_year", "term", "course_codes", "actual_enrollment", "attributed_course_enrollments",
                "units_fixed", "course_sch", "teaching_credit_fraction", "attributed_sch", "enrollment_observation_date"]],
        width="stretch", hide_index=True,
    )

st.subheader("Course leaderboard")
courses = aggregate_courses(activities, academic_years)
courses.insert(0, "Rank", range(1, len(courses) + 1))
st.caption("One offering is one included instructional activity. Cross-listed sections count once; repeated Fall and Spring offerings count separately.")
st.dataframe(
    courses[["Rank", "course_codes", "total_sch", "offerings", "sch_per_offering", "total_actual_enrollment", "department_sch_share"]],
    width="stretch", hide_index=True,
    column_config={
        "course_codes": "Course",
        "total_sch": "Total SCH",
        "offerings": "Number of offerings",
        "sch_per_offering": "SCH per offering",
        "total_actual_enrollment": "Total actual enrollment",
        "department_sch_share": st.column_config.NumberColumn("Department SCH share", format="percent"),
    },
)

st.subheader("Course drill-down")
selected_course = st.selectbox("Course", courses.course_codes.tolist())
course_detail = activities[
    activities.academic_year.isin(academic_years)
    & (activities.course_codes == selected_course)
    & ~activities.excluded_from_sch.astype(str).str.lower().eq("true")
].sort_values(["academic_year", "term"])
st.caption("Offerings and full course SCH")
st.dataframe(
    course_detail[["academic_year", "term", "course_codes", "actual_enrollment", "units_fixed", "course_sch",
                   "instructors", "section_count", "enrollment_observation_date"]],
    width="stretch", hide_index=True,
)
course_activity_ids = set(course_detail.activity_id)
course_attributions = attrib[attrib.activity_id.isin(course_activity_ids)].sort_values(["academic_year", "term", "faculty"])
st.caption("Instructor attributions")
st.dataframe(
    course_attributions[["academic_year", "term", "faculty", "faculty_category", "actual_enrollment",
                         "attributed_course_enrollments", "teaching_credit_fraction", "attributed_sch"]],
    width="stretch", hide_index=True,
)

st.subheader("Academic-year trends")
trend_dept = dept[dept.academic_year.isin(academic_years)].sort_values("academic_year")
trend_a, trend_b = st.columns(2)
with trend_a:
    st.caption("Total attributed SCH")
    st.line_chart(trend_dept.set_index("academic_year")[["total_attributed_sch"]])
    st.caption("Regular and non-regular SCH shares")
    st.line_chart(trend_dept.set_index("academic_year")[["regular_sch_share", "non_regular_sch_share"]])
with trend_b:
    st.caption("Department SCH/FTE definitions")
    st.line_chart(trend_dept.set_index("academic_year")[["sch_per_fte_all", "sch_per_fte_regular_denominator"]])
    if selected_faculty:
        selected_trend = faculty[
            faculty.academic_year.isin(academic_years) & (faculty.faculty == selected_faculty)
        ].sort_values("academic_year").set_index("academic_year")[["attributed_sch"]]
        st.caption(f"{selected_faculty}: attributed SCH")
        st.line_chart(selected_trend)

st.subheader("Data-quality disclosure")
selected_activities = activities[activities.academic_year.isin(academic_years)]
st.write({
    "early enrollment observations": int(selected_activities.early_enrollment_observation.astype(str).str.lower().eq("true").sum()),
    "variable-unit activities excluded": int(d["excluded_variable_unit_activities"]),
    "CIVENG 190 pilot activities excluded": int(d["excluded_civeng_190_policy_activities"]),
    "CIVENG/ENGIN 98 and 198 activities excluded": int(d["excluded_98_198_policy_activities"]),
    "activities awaiting manual review": int(selected_activities.manual_review_flag.astype(str).str.lower().eq("true").sum()),
})
