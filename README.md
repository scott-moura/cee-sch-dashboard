# CEE Student Credit Hour Dashboard

This repository implements the validated six-semester CEE Student Credit Hour
(SCH) analysis for Fall 2023 through Spring 2026. It preserves source
lineage, separates ingestion from calculation, and keeps faculty and course
decisions behind explicit manual-review gates.

`config/terms_v1.1.json` preserves the locked four-semester Version 1.1 scope;
`config/terms_v1.2.json` defines the validated six-semester scope. Version 1.2
delta-audit files are under `data/audit/v1_2_*.csv`; the dashboard remains
gated automatically if any SCH-impact review queue reopens.

## Methodology encoded here

- Undergraduate courses have a numeric catalog component of 199 or less.
- Variable-unit courses are retained but contribute zero Version 1 SCH.
- Every CIVENG 190 offering is retained for audit but excluded by explicit
  course policy because 190 is a reusable pilot-course number whose sections
  represent heterogeneous proposed courses and instructors.
- Exact CIVENG/ENGIN 98 and 198 group-study listings are retained for audit but
  excluded consistently across every included semester.
- Reviewed room-share/cross-list exceptions may use a section-specific fixed
  unit value from `config/fixed_unit_activity_overrides.csv`. The pipeline
  fails rather than applying an override if refreshed source units no longer
  match the approved value.
- Secondary sections contribute zero SCH.
- Cross-lists and reviewed parallel-delivery sections are grouped into one
  instructional activity; enrollment across distinct listings is summed.
- Primary-class instructor names are deduplicated and teaching credit is split
  equally. Non-CEE co-instructors remain in the divisor.
- Reviewed GSIs/TAs in `config/instructor_resolutions.csv` are retained in
  lineage fields but removed from the teaching-credit divisor.
- CIVENG activities with named instructors who do not match the roster are
  retained with zero SCH pending review. `data/audit/course_review_actionable.csv`
  reports their potential SCH so high-impact cases can be reviewed first.
  `data/audit/course_review_actionable_sch.csv` is the focused subset whose
  resolution can change Version 1 SCH; it is sorted from highest to lowest
  potential SCH.

For unmatched-instructor review, use `ADD_FACULTY_ALIAS` for a schedule-name
variant of someone already on the roster, `ADD_CEE_NON_REGULAR` for an
affiliated lecturer or other non-regular instructor, `INCLUDE_NON_CEE_CO_INSTRUCTOR`
for an actual non-CEE co-instructor who must remain in the allocation divisor,
`EXCLUDE_GSI_TA` for instructional support, `EXCLUDE_NOT_CEE_AFFILIATED` when
the activity has no attributable CEE instructor, or `NEEDS_RESEARCH` when the
evidence is inconclusive.
- The latest available public enrollment observation is used, even when early;
  observations more than 14 days before term end are flagged.
- Academic-year FTE is average semester FTE: faculty-semesters divided by two.
- Every current roster member is assumed affiliated in all six Version 1.2 terms and
  remains in the denominator even with zero qualifying SCH.
- Reviewed historical/non-roster CEE instructors are stored in
  `config/supplemental_faculty_affiliations.csv` and enter the denominator only
  for their individually approved affiliated semesters.
- The approved 65-person classification set is checksum-locked in
  `config/faculty_classification_approval.json`; any roster/category drift
  automatically reopens the faculty audit.
- The approved course edge-case sample is persisted in
  `config/manual_validation_approval.csv`; pipeline refreshes reapply those
  decisions by audit category and instructional-activity ID.

## Source files

The dated faculty HTML snapshot is tracked in `data/raw/cee/`. The BerkeleyTime
MongoDB archive is deliberately ignored by Git because it is 145 MB; its SHA-256
and retrieval URL are recorded in `config/source_manifest.json`.

The pipeline consumes newline-delimited relaxed JSON exports of BerkeleyTime's
`sections`, `classes`, and `enrollmenthistories` collections. To reproduce the
current run after restoring the public archive into MongoDB, export the six
target terms and run:

```bash
python -m sch_dashboard.pipeline \
  --sections /path/to/sections.jsonl \
  --classes /path/to/classes.jsonl \
  --enrollments /path/to/enrollmenthistories.jsonl \
  --terms-config config/terms_v1.2.json

python -m sch_dashboard.v12_audit \
  --sections /path/to/sections.jsonl
```

Generated CSVs, audit queues, and `sch.duckdb` are written beneath
`data/processed/` and `data/audit/`.

## Local dashboard

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/streamlit run dashboard/app.py
```

The dashboard identifies the latest-observation enrollment basis and links
every aggregate to course-level records. The Version 1.2 faculty, instructor,
grouping, unit, and data-quality gates are approved; publication still
requires the department's normal review and governance process.

The academic-year filter accepts one or more years. Headline metrics and
faculty rankings aggregate the selected years, with SCH/FTE calculated from
total SCH divided by total selected-period FTE-years. The course leaderboard
groups repeated offerings by course identity, treats each reviewed cross-list
as one course, and reports both total SCH and SCH per offering.

## Tests

```bash
.venv/bin/pytest
```
