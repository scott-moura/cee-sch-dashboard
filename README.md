# CEE Student Credit Hour Dashboard

This repository implements the four-semester CEE Student Credit Hour (SCH)
proof of concept for Fall 2024 through Spring 2026. It preserves source
lineage, separates ingestion from calculation, and keeps faculty and course
decisions behind explicit manual-review gates.

## Methodology encoded here

- Undergraduate courses have a numeric catalog component of 199 or less.
- Variable-unit courses are retained but contribute zero Version 1 SCH.
- Secondary sections contribute zero SCH.
- Cross-lists and reviewed parallel-delivery sections are grouped into one
  instructional activity; enrollment across distinct listings is summed.
- Primary-class instructor names are deduplicated and teaching credit is split
  equally. Non-CEE co-instructors remain in the divisor.
- The latest available public enrollment observation is used, even when early;
  observations more than 14 days before term end are flagged.
- Academic-year FTE is average semester FTE: faculty-semesters divided by two.
- Every current roster member is assumed affiliated in all four POC terms and
  remains in the denominator even with zero qualifying SCH.

## Source files

The dated faculty HTML snapshot is tracked in `data/raw/cee/`. The BerkeleyTime
MongoDB archive is deliberately ignored by Git because it is 145 MB; its SHA-256
and retrieval URL are recorded in `config/source_manifest.json`.

The pipeline consumes newline-delimited relaxed JSON exports of BerkeleyTime's
`sections`, `classes`, and `enrollmenthistories` collections. To reproduce the
current run after restoring the public archive into MongoDB, export the four
target terms and run:

```bash
python -m sch_dashboard.pipeline \
  --sections /path/to/sections.jsonl \
  --classes /path/to/classes.jsonl \
  --enrollments /path/to/enrollmenthistories.jsonl
```

Generated CSVs, audit queues, and `sch.duckdb` are written beneath
`data/processed/` and `data/audit/`.

## Local dashboard

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/streamlit run dashboard/app.py
```

The dashboard visibly identifies provisional data and links every aggregate to
course-level records. Do not treat results as published until the faculty and
course audit files have been approved.

## Tests

```bash
.venv/bin/pytest
```

