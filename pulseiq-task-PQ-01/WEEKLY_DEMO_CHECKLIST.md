# PulseIQ — Weekly Demo Checklist

## Week 1: Data Foundations

**Project:** PulseIQ
**Task:** PQ-01 — ETL and Data Contracts
**Demo date:** Friday, 2026-10-23
**Presenter:** Project intern

### 1. Preparation

* [ ] Confirm the latest code is committed to Git.
* [ ] Confirm the current branch is `task/PQ-01`.
* [ ] Confirm the working tree is clean.
* [ ] Run the ETL pipeline successfully.
* [ ] Review the audit results.
* [ ] Review the quarantine results.
* [ ] Check the README and daily work log.
* [ ] Confirm the demo uses fictional training data only.

### 2. Two-Minute Demo Plan

**0:00–0:20 — Introduction**

* Explain the purpose of PulseIQ and PQ-01.
* Explain why data quality checks are necessary.

**0:20–0:45 — Data loading**

* Show how the source CSV files are loaded into DuckDB.
* Briefly explain the role of the `raw` schema.

**0:45–1:15 — Data quality pipeline**

* Show `run_quality_pipeline.py`.
* Explain how the four contracted feeds are validated.
* Explain how invalid records are quarantined with rejection reasons.

**1:15–1:40 — Results**

* Show the latest verified audit summary.
* Explain the 29,775 received records, 29,755 passed records, and 20 quarantined task records.
* Explain the two identified task rejection reasons.

**1:40–2:00 — Git and next steps**

* Show the `task/PQ-01` branch and commit history.
* Explain remaining contract verification work and the next steps.

### 3. Questions to Practise

* Why do we use DuckDB?
* What is a data contract?
* Why are rejected rows quarantined instead of deleted?
* What does the ETL audit table record?
* Why are 20 task records quarantined?
* What is the difference between a Git commit and a branch?
* Which contract requirements still need verification?

### 4. Final Review

* [ ] I can explain the important parts of the code in my own words.
* [ ] I can run the pipeline without assistance.
* [ ] I can explain the audit counts.
* [ ] I can explain the quarantine reasons.
* [ ] I can distinguish verified results from outstanding work.
* [ ] I have recorded the two-minute demo.
* [ ] I have saved the demo recording in the required location.

### 5. Reflection

**What went well?**

*To be completed after the demo.*

**What was difficult?**

*To be completed after the demo.*

**What will I improve next week?**

*To be completed after the demo.*
