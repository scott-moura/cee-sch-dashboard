from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"

st.set_page_config(page_title="CEE SCH Dashboard", layout="wide")
st.title("CEE Undergraduate Student Credit Hours")
st.caption("Provisional proof of concept · Latest available public enrollment observations")
st.warning("SCH is an instructional credit-hour diagnostic, not a measure of total faculty workload or performance. Variable-unit courses are excluded.")

required = ["faculty_academic_year.csv", "department_academic_year.csv", "instructor_attributions.csv"]
if not all((DATA / x).exists() for x in required):
    st.error("Processed data are missing. Run the pipeline described in README.md.")
    st.stop()

faculty = pd.read_csv(DATA / "faculty_academic_year.csv")
dept = pd.read_csv(DATA / "department_academic_year.csv")
attrib = pd.read_csv(DATA / "instructor_attributions.csv")
activities = pd.read_csv(DATA / "instructional_activities.csv")

ay = st.sidebar.selectbox("Academic year", sorted(faculty.academic_year.unique(), reverse=True))
category = st.sidebar.multiselect("Faculty category", ["REGULAR", "NON_REGULAR", "REVIEW"], default=["REGULAR", "NON_REGULAR", "REVIEW"])
f = faculty[(faculty.academic_year == ay) & faculty.faculty_category.isin(category)].copy()
d = dept[dept.academic_year == ay].iloc[0]

cards = st.columns(4)
cards[0].metric("Total attributed SCH", f"{d.total_attributed_sch:,.1f}")
cards[1].metric("Regular attributed SCH", f"{d.regular_attributed_sch:,.1f}")
cards[2].metric("Non-regular attributed SCH", f"{d.non_regular_attributed_sch:,.1f}")
cards[3].metric("Variable-unit activities excluded", f"{int(d.excluded_variable_unit_activities):,}")
cards = st.columns(4)
cards[0].metric("Regular SCH share", f"{d.regular_sch_share:.1%}")
cards[1].metric("Non-regular SCH share", f"{d.non_regular_sch_share:.1%}")
cards[2].metric("SCH/FTE — all faculty", f"{d.sch_per_fte_all:,.1f}")
cards[3].metric("SCH/FTE — regular denominator", f"{d.sch_per_fte_regular_denominator:,.1f}")

st.subheader("Faculty leaderboard")
f = f.sort_values(["attributed_sch", "faculty"], ascending=[False, True]).reset_index(drop=True)
f.insert(0, "Rank", range(1, len(f) + 1))
f["department_sch_share"] = f.attributed_sch / d.total_attributed_sch if d.total_attributed_sch else 0
st.dataframe(f[["Rank", "faculty", "title", "faculty_category", "attributed_sch", "qualifying_primary_courses", "attributed_course_enrollments", "department_sch_share"]], width="stretch", hide_index=True)

st.subheader("Faculty drill-down")
selected = st.selectbox("Faculty member", f.faculty.tolist())
detail = attrib[(attrib.academic_year == ay) & (attrib.faculty == selected)].copy()
terms = ["All"] + sorted(detail.term.dropna().unique().tolist())
term_filter = st.selectbox("Semester", terms)
if term_filter != "All":
    detail = detail[detail.term == term_filter]
subjects = sorted({code.split(" ")[0] for value in detail.course_codes.dropna() for code in value.split(" | ")})
subject_filter = st.selectbox("Subject/course", ["All"] + subjects)
if subject_filter != "All":
    detail = detail[detail.course_codes.str.contains(subject_filter, regex=False)]
st.dataframe(detail[["term", "course_codes", "actual_enrollment", "attributed_course_enrollments", "units_fixed", "course_sch", "teaching_credit_fraction", "attributed_sch", "enrollment_observation_date"]], width="stretch", hide_index=True)

st.subheader("Academic-year trends")
trend_a, trend_b = st.columns(2)
with trend_a:
    st.caption("Total attributed SCH")
    st.line_chart(dept.set_index("academic_year")[["total_attributed_sch"]])
    st.caption("Regular and non-regular SCH shares")
    st.line_chart(dept.set_index("academic_year")[["regular_sch_share", "non_regular_sch_share"]])
with trend_b:
    st.caption("Department SCH/FTE definitions")
    st.line_chart(dept.set_index("academic_year")[["sch_per_fte_all", "sch_per_fte_regular_denominator"]])
    selected_trend = faculty[faculty.faculty == selected].set_index("academic_year")[["attributed_sch"]]
    st.caption(f"{selected}: attributed SCH")
    st.line_chart(selected_trend)

st.subheader("Data-quality disclosure")
ay_activities = activities[activities.academic_year == ay]
st.write({
    "early enrollment observations": int(ay_activities.early_enrollment_observation.astype(str).str.lower().eq("true").sum()),
    "variable-unit activities excluded": int(d.excluded_variable_unit_activities),
    "activities awaiting manual review": int(ay_activities.manual_review_flag.astype(str).str.lower().eq("true").sum()),
})
