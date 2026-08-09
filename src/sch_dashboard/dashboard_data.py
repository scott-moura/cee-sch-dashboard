from __future__ import annotations

import pandas as pd


def aggregate_department(department: pd.DataFrame, academic_years: list[str]) -> dict[str, float]:
    selected = department[department["academic_year"].isin(academic_years)]
    total = float(selected["total_attributed_sch"].sum())
    regular = float(selected["regular_attributed_sch"].sum())
    non_regular = float(selected["non_regular_attributed_sch"].sum())
    all_fte = float(selected["all_faculty_annual_fte"].sum())
    regular_fte = float(selected["regular_annual_fte"].sum())
    return {
        "total_attributed_sch": total,
        "regular_attributed_sch": regular,
        "non_regular_attributed_sch": non_regular,
        "regular_sch_share": regular / total if total else 0.0,
        "non_regular_sch_share": non_regular / total if total else 0.0,
        "all_faculty_annual_fte": all_fte,
        "regular_annual_fte": regular_fte,
        "sch_per_fte_all": total / all_fte if all_fte else 0.0,
        "sch_per_fte_regular_denominator": total / regular_fte if regular_fte else 0.0,
        "excluded_variable_unit_activities": float(selected["excluded_variable_unit_activities"].sum()),
        "excluded_course_policy_activities": float(selected["excluded_course_policy_activities"].sum()),
        "excluded_civeng_190_policy_activities": float(selected["excluded_civeng_190_policy_activities"].sum()),
        "excluded_98_198_policy_activities": float(selected["excluded_98_198_policy_activities"].sum()),
    }


def aggregate_faculty(faculty: pd.DataFrame, academic_years: list[str], categories: list[str]) -> pd.DataFrame:
    selected = faculty[
        faculty["academic_year"].isin(academic_years) & faculty["faculty_category"].isin(categories)
    ]
    result = selected.groupby(
        ["faculty_id", "faculty", "title", "faculty_category"], as_index=False, dropna=False
    ).agg(
        selected_period_fte=("annual_fte", "sum"),
        attributed_sch=("attributed_sch", "sum"),
        attributed_course_enrollments=("attributed_course_enrollments", "sum"),
        qualifying_offerings=("qualifying_primary_courses", "sum"),
    )
    return result.sort_values(["attributed_sch", "faculty"], ascending=[False, True]).reset_index(drop=True)


def aggregate_courses(activities: pd.DataFrame, academic_years: list[str]) -> pd.DataFrame:
    selected = activities[activities["academic_year"].isin(academic_years)].copy()
    included = ~selected["excluded_from_sch"].astype(str).str.lower().eq("true")
    selected = selected[included]
    result = selected.groupby("course_codes", as_index=False).agg(
        total_sch=("course_sch", "sum"),
        offerings=("activity_id", "nunique"),
        total_actual_enrollment=("actual_enrollment", "sum"),
    )
    result["sch_per_offering"] = result["total_sch"] / result["offerings"]
    period_total = float(result["total_sch"].sum())
    result["department_sch_share"] = result["total_sch"] / period_total if period_total else 0.0
    return result.sort_values(["total_sch", "course_codes"], ascending=[False, True]).reset_index(drop=True)
