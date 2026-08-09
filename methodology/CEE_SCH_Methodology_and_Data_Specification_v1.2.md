# CEE Student Credit Hour (SCH) Analysis
## Methodology and Data Specification

**Version 1.2 — Validated Six-Semester Specification — August 8, 2026**

## 1. Purpose

This document defines the analytical contract for measuring undergraduate Student Credit Hour (SCH) production attributable to instructors affiliated with the UC Berkeley Department of Civil & Environmental Engineering (CEE).

Version 1.2 covers Fall 2023 through Spring 2026: six semesters across three academic years. It retains semester detail and reports primarily by academic year. The intended future expansion remains Fall 2019 through Spring 2026, excluding summers.

The dashboard is an instructional credit-hour diagnostic. It is not a comprehensive measure of workload or performance. Research, administration, advising, service, leaves, course releases, buyouts, and other responsibilities are outside the calculation.

## 2. Revision History

### Version 1.2

Version 1.2 extends the validated calculation and audit framework from four to six semesters. It:

- adds Fall 2023 and Spring 2024, producing AY 2023-24 through AY 2025-26;
- extends the approved current-roster affiliation assumption to both added semesters;
- adds reviewed aliases and term-specific supplemental CEE instructors found in the added terms;
- persists all instructor-credit decisions from the prioritized delta audit, including non-CEE co-instructors, GSIs/TAs, and non-affiliated instructors;
- groups the reviewed Fall 2023 and Spring 2024 `CIVENG 190S` parallel sections and the Fall 2023 `GPP 196` sections as coordinated instructional activities;
- records the reviewed Spring 2024 `CIVENG C30 | MECENG C85` offerings as separate activities;
- applies reviewed enrollment overrides to two source listings with missing public observations;
- applies a reviewed three-unit fixed-unit exception to Spring 2024 `CIVENG C30 | MECENG C85`; and
- excludes exact `CIVENG 98`, `CIVENG 198`, `ENGIN 98`, and `ENGIN 198` group-study listings across all included terms, in addition to exact `CIVENG 190` pilot offerings.

All Version 1.2 delta-audit queues are resolved, the deployment gate is cleared, and Version 1.1 remains preserved as the locked four-semester specification.

### Version 1.1

Version 1.1 incorporates decisions reached during proof-of-concept implementation and audit:

- uses BerkeleyTime's dated public production backup and the latest available enrollment observation;
- supports reviewed faculty-name aliases and term-specific supplemental CEE instructors;
- prevents named CIVENG instructors from being silently discarded when they do not match the roster;
- formalizes manual decisions for GSIs/TAs, non-CEE co-instructors, non-affiliated instructors, and non-regular CEE instructors;
- groups reviewed simultaneous/parallel sections as one instructional activity;
- applies a reviewed three-unit override to the Spring 2026 room-share `CIVENG 153 | CYPLAN 190-002`;
- excludes every `CIVENG 190` pilot-course offering by explicit course policy;
- supports combined multi-year dashboard analysis; and
- adds a Course Leaderboard with total SCH, offering count, and SCH per offering.

Version 1.0 remains preserved as the original proof-of-concept specification.

## 3. Analytical Questions

The project answers:

1. How much undergraduate SCH is attributable to each CEE-affiliated instructor by semester and academic year?
2. How does attributed SCH vary across instructors and faculty categories?
3. What share is attributable to REGULAR versus NON-REGULAR instructors?
4. What is department SCH/FTE under all-faculty and regular-faculty denominator definitions?
5. Which courses contribute the most full instructional-activity SCH?
6. What is each course's average SCH per offering?
7. Which underlying offerings and instructor allocations produce each aggregate?
8. How do these measures change across one or more selected academic years?

## 4. Time Period and Aggregation

### 4.1 Included terms

- Fall 2023
- Spring 2024
- Fall 2024
- Spring 2025
- Fall 2025
- Spring 2026

Summer sessions are excluded.

### 4.2 Academic years

- AY 2023-24 = Fall 2023 + Spring 2024
- AY 2024-25 = Fall 2024 + Spring 2025
- AY 2025-26 = Fall 2025 + Spring 2026

Semester records must remain available for drill-down.

### 4.3 Multiple-year selections

When multiple academic years are selected, headline SCH and faculty rankings use combined totals. FTE is summed as FTE-years across the selected academic years. Combined SCH/FTE is therefore:

**SelectedPeriodSCHPerFTE = TotalSelectedPeriodAttributedSCH / TotalSelectedPeriodFTEYears**

## 5. Student Credit Hour Definition

For instructional activity c:

**SCH_c = Σ_s Units_(s,c)**

For an activity in which each enrolled student receives a fixed unit value U:

**SCH_c = LatestAvailableEnrollment_c × U_c**

For cross-listed or reviewed room-shared activities, enrollment is summed across distinct primary listings and counted once per enrolled student/listing record represented by the shared activity.

## 6. Course Scope and Exclusions

### 6.1 Undergraduate scope

Include catalog numbers whose numeric component is 199 or less. Prefixes and suffixes such as `C`, `H`, or `A` do not change the numeric test.

A course need not carry the CIVENG subject. An undergraduate course in another subject contributes when an in-scope CEE-affiliated instructor receives teaching credit.

### 6.2 Variable-unit rule

Version 1 excludes variable-unit activities because individual students' selected units are not present in the public source. Excluded records remain in processed data with:

- `excluded_from_sch = true`;
- `exclusion_reason = VARIABLE_UNITS`;
- available enrollment and unit bounds; and
- source identifiers and audit lineage.

### 6.3 Reviewed fixed-unit exception

A narrowly scoped configuration override may treat a source-flagged activity as fixed-unit only when all linked sections have the same section-specific minimum and maximum units and the project owner approves the exception.

The approved exceptions are:

- Spring 2024 `CIVENG C30 | MECENG C85`, taught by Panayiotis Papadopoulos: both linked listings have a reviewed fixed value of three units. The activity remains excluded from CEE-attributed SCH because its sole instructor is not CEE-affiliated.
- Spring 2026 `CIVENG 153 | CYPLAN 190-002`: both primary listings are fixed at three units even though the CYPLAN source record carries a variable-unit attribute. The activity includes 41 CIVENG students and 10 CYPLAN students, so `(41 + 10) × 3 = 153 SCH`, all attributed to Marta Gonzalez.

The pipeline must fail rather than apply either override if refreshed source unit values cease to equal the approved value.

### 6.4 Course-policy exclusions

Exclude every course listing whose exact subject and catalog number are `CIVENG 190`.

`CIVENG 190` is a reusable number for piloting proposed courses. Different sections can represent unrelated topics, instructors, unit structures, and future permanent courses. Combining or comparing these sections as one stable course would be analytically misleading.

Each offering remains in processed and audit data with:

- `excluded_from_sch = true`;
- `exclusion_reason = COURSE_POLICY_EXCLUSION`;
- `course_policy_exclusion = true`; and
- the reason for the policy decision.

The `CIVENG 190` exclusion applies only to exact `CIVENG 190`. It does not apply to `CIVENG 190S`, `CYPLAN 190`, or other subjects/catalog numbers containing 190.

Also exclude every exact `CIVENG 98`, `CIVENG 198`, `ENGIN 98`, and `ENGIN 198` listing across all included semesters. These group-study course numbers are excluded consistently regardless of observed SCH impact. They remain in processed and audit data with the same course-policy flags and exclusion reason.

## 7. Instructional Activities and Section Relationships

### 7.1 Primary and secondary sections

SCH is produced only by primary, credit-bearing listings. Discussion, lab, recitation, and other linked secondary sections receive zero SCH because their credit is already represented by the primary listing.

Secondary sections remain in `course_offerings.csv` for auditability.

### 7.2 Cross-listed courses

Source-identified cross-listed primary sections are grouped into one instructional activity. The shared activity receives one SCH calculation and one teaching-credit allocation.

### 7.3 Reviewed parallel delivery

Simultaneous sections that represent one instructional activity may be grouped through explicit configuration. Approved cases include:

- Fall 2023 CIVENG 190S sections 001 and 002;
- Fall 2023 GPP 196 sections 001 and 002;
- Spring 2024 CIVENG 190S sections 001 and 002;
- Fall 2024 CIVENG 190S sections 001 and 002;
- Spring 2025 CIVENG 190S sections 001 and 003; and
- Spring 2026 CIVENG 187 sections 001 and 002.

The in-person/online delivery distinction does not create separate SCH activities when the sections are simultaneous versions of the same instruction.

## 8. Enrollment Snapshot

Use the chronologically latest valid enrollment observation available in the BerkeleyTime public backup for each source section.

The observation date must be retained. An observation more than 14 days before the configured term end is flagged as early. Fall 2024 and Spring 2025 are knowingly based on the latest public observations even though those observations are not end-of-term counts.

The dashboard must call these values the latest available public enrollment observations, not official Registrar census or completed-course counts.

When the public backup contains no enrollment observation, a project-owner-supplied section enrollment may be used only through a durable override that records the activity, term, section, value, source note, and approval. Version 1.2 contains two such overrides: Fall 2023 `CIVENG C103N` section 29208 has enrollment 59, producing a reviewed 81-student cross-listed activity after the `ESPM C130` and `GEOG C136` listings are included; and Spring 2024 `CYPLAN C88` section 14886 has enrollment 17, producing a reviewed 42-student cross-listed activity after the `CIVENG C88` listing is included. The observation date is unknown and must remain labeled as a manual override.

## 9. Instructor Identification and Manual Review

### 9.1 Primary instructors

Include actual instructors of the primary class. Do not attribute faculty SCH to GSIs, TAs, readers, or instructional-support personnel.

### 9.2 No silent instructor exclusions

Every undergraduate CIVENG activity must remain visible when its named primary instructor does not match the approved roster. Such an activity is assigned zero SCH pending review and records its potential SCH so high-impact cases can be prioritized.

Outside-CIVENG courses enter scope when at least one instructor resolves to a CEE-affiliated person. Any unmatched co-instructor must then be reviewed before attribution.

### 9.3 Review decisions

Permitted reviewed outcomes are:

- `ADD_FACULTY_ALIAS`: map a source-name variant to an existing faculty record;
- `ADD_CEE_NON_REGULAR`: add a term-specific CEE-affiliated non-regular instructor;
- `INCLUDE_NON_CEE_CO_INSTRUCTOR`: retain an actual non-CEE co-instructor in the allocation divisor without adding CEE FTE;
- `EXCLUDE_GSI_TA`: remove instructional support from the primary-instructor divisor;
- `EXCLUDE_NOT_CEE_AFFILIATED`: retain audit lineage but produce no CEE attribution when no CEE-affiliated instructor remains; and
- `NEEDS_RESEARCH`: leave the activity gated at zero SCH.

All decisions must be stored in configuration and regenerated outputs must not erase them.

### 9.4 Team teaching

When N actual primary instructors teach an included activity and contact-hour allocations are unavailable:

**InstructorShare_(i,c) = 1 / N**

**AttributedSCH_(i,c) = SCH_c / N**

Non-CEE co-instructors remain in N. Their shares do not enter the CEE faculty numerator or CEE FTE denominator.

For example, Spring 2025 `ESPM C46 | LS C46` has 368 full course SCH. David L. Sedlak and Whendee Silver each receive 184 SCH. Sedlak's share is CEE-attributed; Silver's is retained as non-CEE attribution and adds no CEE FTE.

## 10. Faculty Population and Classification

### 10.1 Base roster

The base proof-of-concept roster is the dated current CEE faculty webpage snapshot. Its 65 reviewed REGULAR/NON-REGULAR classifications are checksum-locked. Roster or category drift reopens the faculty audit.

The current roster is assumed affiliated in all six Version 1.2 terms, including terms with zero teaching, leave, sabbatical, or other non-teaching status.

### 10.2 Supplemental instructors

Reviewed historical or non-roster CEE instructors are added with term-specific affiliations. The current configuration adds eleven NON-REGULAR instructors. They enter the numerator and denominator only in approved affiliated semesters.

### 10.3 Faculty categories

REGULAR includes Professor, Associate Professor, Assistant Professor, and Teaching Professor-series titles.

NON-REGULAR includes Lecturer, Continuing Lecturer, Adjunct Professor, Professor of the Graduate School, Visiting Professor, Professor In-Residence, and other approved instructor titles outside REGULAR.

GSIs and TAs are excluded from the faculty population.

## 11. FTE Convention

Each affiliated REGULAR or NON-REGULAR person contributes 1.0 faculty-semester per affiliated term.

Annual FTE is the average of Fall and Spring faculty-semester counts:

**AnnualFTE = FacultySemesters / 2**

A person affiliated for one semester contributes 0.5 annual FTE; a person affiliated for both contributes 1.0.

Department metrics are:

**SCH/FTE_All = Total CEE-Attributed SCH / (Regular Annual FTE + Non-Regular Annual FTE)**

**SCH/FTE_RegularDenom = Total CEE-Attributed SCH / Regular Annual FTE**

NON-REGULAR SCH remains in the numerator of both metrics but NON-REGULAR FTE is excluded from the second denominator.

## 12. REGULAR and NON-REGULAR Shares

**RegularSCHShare = RegularAttributedSCH / TotalCEEAttributedSCH**

**NonRegularSCHShare = NonRegularAttributedSCH / TotalCEEAttributedSCH**

For nonzero totals, the two shares must sum to 1.0 within numerical tolerance.

## 13. Course Leaderboard

The Course Leaderboard uses full included instructional-activity SCH once, regardless of how that SCH is divided among instructors.

Within selected academic years:

- repeated Fall and Spring offerings of the same course identity are combined;
- source cross-lists are shown as one course identity;
- reviewed parallel sections count as one offering;
- `Total SCH` is the sum across included offerings;
- `Number of offerings` is the number of distinct included instructional activities; and
- `SCH per offering = Total SCH / Number of offerings`.

Because the Course Leaderboard uses full activity SCH while department totals use only CEE-attributed instructor shares, the Course Leaderboard total can exceed the CEE-attributed department total when a non-CEE co-instructor receives part of an activity.

Course drill-down must show offerings, actual enrollment, units, full course SCH, instructors, and instructor attribution fractions.

## 14. Data Sources and Lineage

### 14.1 BerkeleyTime

The proof of concept uses the public BerkeleyTime production backup retrieved August 8, 2026. The retrieval URL, local path, date, and SHA-256 digest are stored in `config/source_manifest.json`.

The backup is a public, redacted source and is not assumed to be comprehensive institutional data. Authorized UC Berkeley SIS APIs remain the preferred future source if credentials and permission become available.

### 14.2 Faculty roster

The base roster uses the CEE faculty webpage snapshot retrieved August 8, 2026. The raw HTML is preserved.

### 14.3 Manual configuration

Manual decisions never overwrite raw records. Durable configuration includes:

- faculty aliases;
- faculty-classification approval;
- supplemental faculty affiliations;
- instructor resolutions;
- instructional-activity grouping overrides;
- fixed-unit activity overrides;
- course-policy exclusions;
- enrollment overrides and data-quality resolutions;
- activity-grouping resolutions;
- Version 1.2 faculty-affiliation approval; and
- manual edge-case validation approval.

## 15. Analytical Tables

The pipeline produces:

- `faculty_roster.csv`;
- `course_offerings.csv`;
- `instructional_activities.csv`;
- `instructor_attributions.csv`;
- `faculty_semester.csv`;
- `faculty_academic_year.csv`;
- `department_academic_year.csv`;
- course and faculty audit CSVs;
- `validation_report.json`; and
- equivalent DuckDB tables.

Every published aggregate must trace to activity, section, enrollment-observation, instructor, and configuration records.

## 16. Calculation Sequence

For each configured term:

1. Load the approved base roster, aliases, and supplemental term affiliations.
2. Load sections, classes, and enrollment histories from the dated source exports.
3. Restrict the numeric catalog component to 199 or less and exclude summers.
4. Identify primary and linked secondary sections.
5. Group source cross-lists and approved parallel sections into instructional activities.
6. Retain CIVENG activities with unmatched instructors for audit rather than discarding them.
7. Resolve aliases, CEE affiliation, non-CEE participation, and GSI/TA exclusions.
8. Obtain the latest available enrollment for each primary listing.
9. determine section units and apply only validated fixed-unit overrides.
10. Apply the exact `CIVENG 190`, `CIVENG 98`, `CIVENG 198`, `ENGIN 98`, and `ENGIN 198` policy exclusions.
11. Apply variable-unit, missing-data, unresolved-instructor, and no-CEE-instructor exclusions.
12. Compute full course SCH for included activities.
13. Split SCH and enrollment equally among actual primary instructors.
14. Aggregate CEE-attributed shares to faculty-semester and academic year.
15. Complete zero-SCH rows for every affiliated faculty-semester.
16. Calculate department category shares and both FTE metrics.
17. Build combined-year faculty and course leaderboard views.
18. Run automated validation and preserve manual-audit status.

## 17. Validation Requirements

Automated checks must verify:

- no summer terms;
- no catalog numeric component above 199;
- attributed SCH and fractions conserve full activity SCH;
- secondary-section SCH is zero;
- ordinary variable-unit activity SCH is zero;
- all exact `CIVENG 190`, `CIVENG 98`, `CIVENG 198`, `ENGIN 98`, and `ENGIN 198` activity SCH is zero with `COURSE_POLICY_EXCLUSION`;
- fixed-unit overrides still match all linked source section units;
- faculty and department aggregates reconcile;
- REGULAR and NON-REGULAR shares reconcile;
- non-CEE instructors add no CEE FTE;
- supplemental instructors contribute FTE only in approved terms; and
- all SCH-impact unmatched-instructor cases are resolved before final use.

The reviewed manual sample must include large, small, team-taught, cross-listed, linked-section, variable-unit, NON-REGULAR, and outside-CIVENG examples.

## 18. Dashboard Requirements

The dashboard must:

- allow one or more academic years to be selected;
- combine headline metrics and faculty rankings across selected years;
- show total, REGULAR, and NON-REGULAR attributed SCH;
- show category shares and both SCH/FTE definitions;
- provide a faculty leaderboard and course-level attribution drill-down;
- provide a Course Leaderboard and instructor-attribution drill-down;
- show total SCH, number of offerings, and SCH per offering for courses;
- show academic-year trends; and
- disclose early enrollment observations, manual enrollment overrides, variable-unit exclusions, and course-policy exclusions.

The dashboard must visibly state that all exact `CIVENG 190` pilot-course listings and exact `CIVENG/ENGIN 98` and `198` group-study listings are excluded.

## 19. Interpretation Caveats

1. SCH measures instructional credit-hour production, not total workload or performance.
2. Variable-unit activities are excluded except for explicitly reviewed fixed-unit section exceptions.
3. All exact `CIVENG 190` offerings are excluded as heterogeneous pilot-course sections, and exact `CIVENG/ENGIN 98` and `198` group-study listings are excluded consistently across all included semesters.
4. The current roster is the proof-of-concept affiliation baseline; supplemental historical affiliations are term-specific manual decisions.
5. Team teaching is allocated equally because contact-hour distributions are unavailable.
6. Enrollment uses latest available public observations and can differ from official institutional counts.
7. The simplified FTE convention does not represent payroll percentage or workload allocation.
8. Leaves, course releases, research, advising, administration, and service are not normalized.
9. Course retirement or consolidation decisions should not be based on SCH alone; curricular role, accreditation, sequencing, equity, and strategic value require separate evaluation.

## 20. Acceptance Criteria

The proof of concept is accepted when:

1. all six terms are represented;
2. raw sources and digests are preserved;
3. roster and historical affiliation decisions are durable;
4. all SCH-impact instructor exceptions are resolved;
5. cross-lists, parallel sections, and secondary sections avoid double counting;
6. variable-unit and all course-policy exclusions are explicit;
7. approved fixed-unit exceptions are source-validated;
8. faculty, department, and course aggregates reconcile according to their defined grains;
9. manual validation gates are approved;
10. automated validation has zero errors; and
11. dashboard aggregates drill down to source-grounded course records.

## 21. Version-Control Rule

This specification is the analytical contract for Version 1.2. Any subsequent change to inclusion policy, instructor attribution, affiliation/FTE treatment, enrollment selection, cross-list grouping, fixed-unit exceptions, or leaderboard grain must increment the document version before historical results are recalculated.
