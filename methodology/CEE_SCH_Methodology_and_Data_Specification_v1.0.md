# CEE Student Credit Hour (SCH) Analysis
## Methodology and Data Specification

**Version 1.0 — Proof-of-Concept Specification — August 8, 2026**

## 1. Purpose

This document defines the methodology, data rules, assumptions, calculations, exclusions, and implementation requirements for measuring Student Credit Hour (SCH) production attributable to faculty affiliated with the UC Berkeley Department of Civil & Environmental Engineering (CEE).

The immediate objective is to create an auditable proof-of-concept covering four semesters—Fall 2024, Spring 2025, Fall 2025, and Spring 2026—and to report results primarily by **academic year (two-semester aggregation)**. The long-term objective is to extend the same reproducible pipeline to Fall 2019 through Spring 2026 and support an internal dashboard for the CEE Strategic Planning Committee and Department Chair.

The dashboard is intended as a **teaching-workload diagnostic**, not a comprehensive measure of faculty effort or productivity. Research, administration, advising, service, leaves, course buyouts, and other responsibilities are outside the calculation and should be considered separately when interpreting results.

## 2. Primary Analytical Questions

The project should answer the following questions:

1. How much undergraduate SCH is attributable to each named CEE faculty member in each semester and academic year?
2. How does undergraduate SCH vary across faculty members?
3. What share of CEE-affiliated faculty SCH is attributable to REGULAR versus NON-REGULAR faculty?
4. What is department-level SCH/FTE under two alternative denominator definitions?
5. Which courses account for each faculty member's SCH contribution?
6. How do these quantities change over time?

## 3. Time Period

### 3.1 Proof of concept

Include:
- Fall 2024
- Spring 2025
- Fall 2025
- Spring 2026

Exclude:
- Summer sessions

### 3.2 Primary reporting period

The principal aggregation period is one **academic year**, defined as Fall + the immediately following Spring semester.

Therefore:
- AY 2024-25 = Fall 2024 + Spring 2025
- AY 2025-26 = Fall 2025 + Spring 2026

Semester-level data must nevertheless be retained and available for drill-down.

### 3.3 Future expansion

The target historical expansion is Fall 2019 through Spring 2026, excluding summers.

## 4. Definition of Student Credit Hour

For a class c, Student Credit Hour is defined as the sum of credit units received by enrolled students:

**SCH_c = Σ_s Units_(s,c)**

For a fixed-unit course in which every enrolled student receives the same number of units U_c, this reduces to:

**SCH_c = FinalEnrollment_c × U_c**

The calculation must use the **latest/final available enrollment count** for the term.

## 5. Course Scope

### 5.1 Undergraduate courses

Include only undergraduate-level courses with a course number of **199 or less**.

Examples in scope include:
- CE 11
- CE 100
- CE C106
- CE H194
- CE 199
- ENGIN courses numbered 199 or less when taught by an in-scope CEE-affiliated instructor

The course does **not** need to carry a CE/CEE subject code. All qualifying undergraduate courses taught by an in-scope CEE-affiliated instructor count toward that person's attributed SCH.

### 5.2 Variable-unit courses — Version 1 rule

Exclude variable-unit courses from the Version 1 SCH numerator because the selected units for individual students are not presently available from the identified public data sources.

Each excluded variable-unit course must remain in the raw/cleaned dataset with:
- an exclusion flag,
- the reason `VARIABLE_UNITS`,
- enrollment,
- minimum units,
- maximum units, where available.

The dashboard should disclose the number of excluded courses and students.

### 5.3 Future variable-unit enhancement

A later version may calculate a range:

**SCH_min = Enrollment × MinimumUnits**

**SCH_max = Enrollment × MaximumUnits**

These lower and upper bounds may then be propagated to faculty- and department-level estimates.

## 6. Primary vs. Secondary Sections

SCH is associated only with the **primary credit-bearing instructional activity**.

Do **not** separately count secondary sections such as:
- discussion sections,
- laboratory sections,
- recitation sections,
- other linked secondary components.

Counting these would double-count student credit hours already represented by the primary course enrollment and units.

Implementation must therefore identify linked primary/secondary section structures and avoid counting a student's units more than once.

## 7. Instructor Scope and Teaching Credit

### 7.1 Included instructors

Include instructors of record who are actually teaching the **primary class**.

Do not include GSIs, TAs, readers, or other instructional support personnel merely because they are associated with discussion/lab/secondary sections.

### 7.2 Team-taught courses

Where multiple qualifying instructors actually teach the primary class and contact-hour allocations are unavailable, use **equal fractional allocation**.

For N qualifying instructors:

**InstructorShare_(i,c) = 1 / N**

**AttributedSCH_(i,c) = SCH_c / N**

All actual primary-class instructors are included in N, whether or not they are affiliated with CEE. Thus, if one CEE professor and one non-CEE professor jointly teach a 400-SCH course, the CEE professor receives 200 attributed SCH.

### 7.3 Instructor attribution audit fields

For each course offering, retain:
- all listed instructors,
- qualifying primary instructors,
- number of qualifying primary instructors,
- allocation fraction assigned to each instructor,
- rationale/flag if manual resolution was required.

## 8. Cross-Listed Courses

Cross-listed courses—often denoted by a `C` before the course number—must be treated as a **single instructional activity** for SCH purposes.

Each enrolled student must count **exactly once**, regardless of which cross-listed course number the student used to enroll.

The data pipeline must therefore identify cross-list bundles or equivalent shared instructional activities and deduplicate enrollment before calculating SCH.

Where a unique shared class/section identifier is available from the source data, it should be preferred over heuristic matching by title, instructor, time, or location.

## 9. Faculty Population and Classification

### 9.1 CEE affiliation

For the proof of concept, use the **current CEE faculty roster** as the initial affiliation roster. Add instructors found in the four-semester teaching data when appropriate and resolve uncertain historical affiliation manually.

For the later Fall 2019-Spring 2026 expansion, build a term-specific historical CEE affiliation roster and manually resolve arrivals, departures, title changes, and unusual appointments.

CEE affiliation controls whether an instructor appears in the CEE faculty leaderboard and contributes to department-level denominator calculations. It does not restrict which subject codes can contribute SCH.

### 9.2 REGULAR faculty

Classify the following as `REGULAR`:
- Professor
- Associate Professor
- Assistant Professor
- Teaching Professor
- Associate Teaching Professor
- Assistant Teaching Professor

For this analysis, Teaching Professor-series faculty are intentionally grouped with ladder-rank Academic Senate faculty as regular faculty for strategic-planning purposes.

### 9.3 NON-REGULAR faculty

Classify all other faculty/instructor titles as `NON_REGULAR`, including, but not limited to:
- Lecturer
- Continuing Lecturer
- Adjunct Professor
- Adjunct Associate Professor
- Adjunct Assistant Professor
- Professor of the Graduate School
- Visiting Professor
- other faculty/instructor titles not included in REGULAR

GSIs/TAs are not faculty for this analysis and are excluded from the faculty population.

## 10. Faculty FTE Convention

The project uses an intentionally simplified counting convention for the internal strategic-planning metric.

### 10.1 Individual faculty

For individual attribution, every named REGULAR or NON-REGULAR faculty member is assigned:

**FTE = 1.0**

Therefore, at the individual level, SCH/FTE is numerically equal to attributed SCH for a full reporting period in which the person is counted once. The dashboard should emphasize **Attributed SCH** as the primary individual metric and label the FTE convention clearly.

### 10.2 Faculty-semester accounting

For academic-year denominator calculations, faculty should be counted by **faculty-semester** when data permit, so that a person affiliated for only one of the two semesters contributes 1.0 faculty-semester rather than being implicitly counted for both semesters.

For the proof of concept, the current roster is the starting point and historical exceptions may be manually resolved.

## 11. Department-Level SCH/FTE Metrics

Calculate two department-level versions.

### 11.1 Metric A — All-faculty denominator

Both REGULAR and NON-REGULAR faculty count as 1.0 FTE (or one faculty-semester per included semester).

**Department SCH/FTE_All = Total Attributed SCH / (Regular FTE + Non-Regular FTE)**

This answers: How much undergraduate SCH is produced per named CEE-affiliated faculty member when all included faculty titles are counted in the denominator?

### 11.2 Metric B — Regular-faculty-only denominator

REGULAR faculty count as 1.0 FTE; NON-REGULAR faculty count as 0.0 FTE in the denominator, while SCH produced by both groups remains in the numerator.

**Department SCH/FTE_RegularDenom = Total Attributed SCH / Regular FTE**

This answers: How much total undergraduate SCH is supported per regular-faculty FTE, including instructional production delivered by non-regular faculty?

The dashboard must label these metrics distinctly to avoid confusion.

## 12. Regular vs. Non-Regular SCH Share

Calculate:

**RegularSCHShare = RegularFacultyAttributedSCH / TotalAttributedSCH**

**NonRegularSCHShare = NonRegularFacultyAttributedSCH / TotalAttributedSCH**

By construction:

**RegularSCHShare + NonRegularSCHShare = 1**

These are key strategic-planning metrics and should be displayed prominently by academic year and over time.

## 13. Enrollment Snapshot

Use the **latest/final available enrollment count** for each course offering in each term.

If the source exposes a time series rather than an explicit `final enrollment` field:
1. identify the chronologically latest valid enrollment observation for the term/course;
2. record its observation timestamp/date;
3. retain the time-series source identifier if available;
4. flag any course for which the latest observation appears materially earlier than the end of the term.

The methodology document and dashboard should refer to this as the **latest/final available enrollment count**, not necessarily an official Registrar census count unless such a source is later obtained.

## 14. BerkeleyTime and Upstream Data Architecture

### 14.1 Identified source

Public Berkeley materials state that BerkeleyTime data are sourced from UC Berkeley's **Student Information System (SIS) Course and Class APIs**. BerkeleyTime is an ASUC student-run application that combines Berkeley academic information into its own application/database.

### 14.2 Direct access to upstream SIS APIs

The upstream SIS APIs should **not be assumed to be anonymously public**. BerkeleyTime's current development documentation includes an `API Sandbox` that explicitly **requires SIS API keys**. Therefore, the prototype should not be designed around unauthenticated direct calls to the campus SIS endpoints unless the project obtains authorized API credentials/access from UC Berkeley.

### 14.3 BerkeleyTime public data backup

BerkeleyTime's current development documentation provides a downloadable **public daily production backup** for local development. It also states that public backups are **redacted and not a comprehensive dataset**, whereas full/private backups require restricted access.

This public backup is an attractive structured source for prototyping because it avoids scraping rendered HTML, but its coverage must be validated against the fields and semesters required for this project.

### 14.4 Recommended source hierarchy for implementation

Use the following hierarchy:

1. **Authorized UC Berkeley SIS Course/Class API access**, if credentials can be obtained and terms permit the use case.
2. **BerkeleyTime structured public data/interface**, including the public development backup or a stable documented BerkeleyTime API/GraphQL endpoint, after confirming required historical enrollment data are present.
3. **BerkeleyTime web application data extraction** as a fallback if structured public data are incomplete.
4. **Rendered HTML scraping** only as a last resort.

The implementation must isolate source-specific logic behind a data-ingestion adapter so the dashboard is not tightly coupled to one website or endpoint.

### 14.5 Prototype recommendation

For the first implementation attempt:
- inspect the BerkeleyTime public backup schema;
- determine whether it contains Fall 2024-Spring 2026 courses, instructors, section relationships, units, cross-list identifiers, and enrollment histories/final counts;
- validate a small sample against the BerkeleyTime enrollment UI;
- use the structured backup if coverage is sufficient;
- otherwise implement a BerkeleyTime public-interface adapter while separately exploring authorized SIS API access.

Do not embed SIS API credentials in frontend/dashboard code. Any authenticated upstream data acquisition should occur in a secure backend/ETL process.

## 15. Core Data Model

The implementation should preserve raw source records and generate normalized analytical tables.

### 15.1 Faculty table

Recommended fields:
- `faculty_id` — internal stable identifier
- `canonical_name`
- `source_name`
- `cee_affiliated` — boolean
- `faculty_category` — REGULAR / NON_REGULAR
- `title`
- `term`
- `fte_value`
- `affiliation_source`
- `manual_override`
- `notes`

### 15.2 Course offering table

Recommended fields:
- `term`
- `academic_year`
- `subject`
- `catalog_number`
- `course_code`
- `course_title`
- `section_id`
- `primary_section_id`
- `crosslist_group_id`
- `section_type`
- `is_primary_section`
- `is_undergraduate`
- `is_variable_units`
- `units_fixed`
- `units_min`
- `units_max`
- `final_enrollment`
- `enrollment_observation_date`
- `source_course_id`
- `source_class_id`

### 15.3 Instructor-course attribution table

Recommended fields:
- `term`
- `course_offering_id`
- `faculty_id`
- `instructor_name_source`
- `is_primary_instructor`
- `is_gsi_ta`
- `qualifying_instructor_count`
- `teaching_credit_fraction`
- `course_sch`
- `attributed_sch`
- `excluded_from_sch`
- `exclusion_reason`
- `manual_review_flag`

### 15.4 Data lineage

Every analytical row should be traceable to source identifiers and, where possible, source URLs or source-record IDs. Manual corrections must never overwrite raw data; they should be represented as explicit overrides with notes.

## 16. Calculation Pipeline

For each term:

1. Load/identify the CEE-affiliated faculty roster.
2. Normalize faculty names and titles.
3. Retrieve all Berkeley course offerings taught by rostered CEE-affiliated instructors.
4. Restrict course numbers to 199 or less.
5. Identify the primary instructional section/activity.
6. Exclude secondary discussion/lab/etc. sections from SCH production.
7. Identify and consolidate cross-listed instructional activities.
8. Obtain latest/final available enrollment.
9. Determine fixed versus variable units.
10. Exclude variable-unit courses from Version 1 SCH while retaining flagged records.
11. Compute course SCH for fixed-unit courses.
12. Identify qualifying actual primary instructors; exclude GSIs/TAs.
13. Allocate teaching credit equally among qualifying primary instructors.
14. Attribute the resulting SCH share to each named instructor.
15. Restrict the CEE leaderboard to CEE-affiliated faculty, but retain non-CEE co-instructors for correct allocation fractions.
16. Aggregate to faculty-semester.
17. Aggregate semester data to academic year.
18. Calculate REGULAR vs. NON-REGULAR shares.
19. Calculate both department SCH/FTE denominator variants.
20. Run validation and exception checks before publishing dashboard output.

## 17. Required Validation and Quality Checks

Before accepting proof-of-concept results, manually audit a sample that includes:
- a large lecture course,
- a small undergraduate course,
- a team-taught course,
- a course co-taught with a non-CEE instructor,
- a cross-listed course,
- a course with linked discussion/lab sections,
- a variable-unit course excluded from SCH,
- a NON-REGULAR faculty instructor,
- a course outside the CE subject taught by a CEE-affiliated instructor.

Automated integrity checks should include:
- no included catalog number > 199;
- no Summer term rows in reported data;
- no GSI/TA SCH attribution;
- teaching-credit fractions sum to 1.0 for each included instructional activity, within numerical tolerance;
- cross-listed activity is counted once;
- secondary-section SCH = 0;
- variable-unit Version 1 SCH = 0 and exclusion flag is present;
- REGULAR + NON-REGULAR attributed SCH equals total CEE-attributed SCH;
- RegularSCHShare + NonRegularSCHShare = 1.0, within numerical tolerance;
- every published aggregate can be traced to underlying course records.

## 18. Dashboard Requirements

### 18.1 Principal leaderboard

Default view: one academic year.

Columns should include:
- Rank
- Faculty
- Title
- Faculty Category (REGULAR / NON-REGULAR)
- Attributed SCH
- Number of qualifying primary courses taught
- Students served, if defined carefully and without double-counting
- Share of department attributed SCH

Because individual FTE is set to 1.0, the primary faculty ranking should use **Attributed SCH**, rather than presenting a redundant individual SCH/FTE column as the headline measure.

### 18.2 Filters/drill-downs

Support:
- Academic Year
- Semester
- REGULAR / NON-REGULAR
- Faculty member
- Subject/course

A faculty drill-down should show each contributing course, final enrollment, units, total course SCH, teaching-credit fraction, and attributed SCH.

### 18.3 Department summary cards

Display at minimum:
- Total attributed undergraduate SCH
- REGULAR faculty attributed SCH
- NON-REGULAR faculty attributed SCH
- Regular SCH share
- Non-Regular SCH share
- Department SCH/FTE — All-faculty denominator
- Department SCH/FTE — Regular-only denominator
- Number of variable-unit courses excluded

### 18.4 Trend views

When multiple academic years are available, plot:
- total SCH by academic year,
- Regular vs. Non-Regular SCH shares,
- both department SCH/FTE definitions,
- faculty-level SCH trends.

## 19. Interpretation Caveats

The dashboard must visibly state that:

1. SCH measures instructional credit-hour production, not total faculty workload or performance.
2. The Version 1 analysis excludes variable-unit courses.
3. Current-roster affiliation is used as the proof-of-concept starting point; historical affiliation will be refined when scaling backward.
4. Individual faculty are assigned a simplified FTE of 1.0 for this internal diagnostic.
5. Team-teaching is allocated equally because contact-hour distributions are unavailable.
6. Enrollment uses the latest/final available public observation and may differ from official institutional census or completed-course records.
7. Administrative assignments, leaves, course releases/buyouts, research, advising, service, and other responsibilities are not normalized in the metric.

## 20. Implementation Principles for Codex / Software Development

The codebase should be designed for reproducibility and auditability.

Recommended architecture:

```text
sch-project/
  README.md
  methodology/
    CEE_SCH_Methodology_and_Data_Specification.md
  config/
    terms.yaml
    faculty_title_mapping.yaml
    exclusions.yaml
  data/
    raw/
    interim/
    processed/
  src/
    ingest/
      berkeleytime_backup.py
      berkeleytime_public_api.py
      sis_api.py
    normalize/
      faculty.py
      courses.py
      instructors.py
      crosslists.py
    calculate/
      sch.py
      teaching_credit.py
      aggregates.py
    validate/
      checks.py
      manual_audit.py
  dashboard/
  tests/
```

Implementation requirements:
- preserve raw data unchanged;
- use deterministic transformations;
- separate ingestion from normalization and calculations;
- treat title-category mapping as configuration, not hard-coded logic scattered through code;
- make exclusion rules explicit and testable;
- retain source IDs and audit fields;
- implement automated unit tests for SCH, team-teaching, cross-listing, variable-unit exclusion, and academic-year aggregation;
- cache historical source data so dashboard rendering does not depend on live external calls;
- keep authenticated API keys/secrets server-side and outside version control;
- produce processed CSV/Parquet outputs that can be independently inspected without the dashboard.

## 21. Proof-of-Concept Acceptance Criteria

The proof of concept is complete when:

1. Fall 2024 through Spring 2026 data are ingested for the current CEE roster and manually resolved affiliation exceptions.
2. All qualifying undergraduate courses, including non-CE subject courses taught by CEE faculty, are represented.
3. Primary/secondary sections and cross-lists are resolved without SCH double-counting.
4. Latest/final available enrollment is used.
5. Variable-unit courses are excluded and visibly flagged.
6. Team-taught courses are fractionally attributed across actual primary instructors.
7. GSIs/TAs receive no faculty SCH attribution.
8. Faculty-level SCH is produced by semester and academic year.
9. REGULAR vs. NON-REGULAR SCH shares are produced.
10. Both department-level SCH/FTE denominator definitions are produced.
11. A manual audit sample has been checked against BerkeleyTime/source records.
12. The dashboard can trace any faculty total back to course-level records.

## 22. Authoritative / Reference Sources

- UC Berkeley Office of Planning and Analysis (OPA), **Rules for Assignment of Teaching Credit**, Class Schedule & Instructional Record (CSIR).
- UC Berkeley Civil & Environmental Engineering, **Faculty directory**.
- BerkeleyTime, **Enrollment** application and open-source repository.
- BerkeleyTime Documentation, **Local Development**, including public backup instructions and SIS API sandbox requirements.
- UC Berkeley Management, Entrepreneurship, & Technology (M.E.T.) academic resources page, which states that BerkeleyTime data are sourced from Berkeley's **Student Information System's Course and Class APIs**.

## 23. Version-Control Note

This document should be stored with the project repository and treated as the analytical contract for Version 1. Any future change to inclusion rules, FTE conventions, enrollment snapshots, title classification, cross-list handling, or variable-unit treatment should update this specification and increment its version before recalculating historical results.
