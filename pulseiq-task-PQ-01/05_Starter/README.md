# PulseIQ — PQ-01: Data Foundations and ETL Pipeline

## 1. Project Overview

PulseIQ is a workforce analytics project for the fictional company Zenith Nova Technologies.

The objective of PQ-01 is to establish a reliable data foundation by loading source data into DuckDB, defining data contracts, validating records, quarantining rejected rows, and recording ETL audit statistics.

## 2. Technology Stack

* Python
* DuckDB
* SQL
* CSV
* Pandas
* Visual Studio Code

## 3. Project Structure

```text
project/
├── 03_Data/
│   ├── csv/
│   └── PulseIQ_Dataset.xlsx
└── 05_Starter/
    ├── load_to_duckdb.py
    ├── run_quality_pipeline.py
    ├── check_contract_coverage.py
    ├── check_audit.py
    ├── check_quarantine.py
    ├── requirements.txt
    ├── metric_views_examples.sql
    ├── demo_users.csv
    ├── pulseiq.duckdb
    └── README.md
```

## 4. Data Loading

The `load_to_duckdb.py` script loads CSV files from the project data folder into DuckDB under the `raw` schema.

The source tables provide the input for data quality validation and downstream analytics.

## 5. Data Contract Overview

The contract definitions are stored in `raw.data_contracts`.

The contract inventory contains 42 column-level rules across four feeds.

| Feed                                      | Contract Rules |
| ----------------------------------------- | -------------: |
| AI anomaly results (`fact_anomaly`)       |             12 |
| AI attrition risk (`fact_attrition_risk`) |              8 |
| AI forecast (`fact_forecast`)             |              9 |
| Task board (`fact_task`)                  |             13 |
| **Total**                                 |         **42** |

The contracts specify column names, logical data types, nullability, and applicable validation requirements.

The `check_contract_coverage.py` script displays the contract inventory and its rule definitions.

## 6. Contract Requirements

### 6.1 AI Anomaly Results — `fact_anomaly`

**12 contract rules**

| Column           | Requirement                                                          |
| ---------------- | -------------------------------------------------------------------- |
| `anomaly_score`  | Required decimal value between 0 and 1                               |
| `employee_id`    | Required string referencing an employee in `dim_employee`            |
| `flagged`        | Required value of `Y` or `N`                                         |
| `model_version`  | Required model-version text                                          |
| `money_at_risk`  | Nullable decimal; blank for attendance records                       |
| `period`         | Required date representing the beginning or end of a month           |
| `reason_code`    | Required published anomaly reason code                               |
| `reason_text`    | Required plain-English explanation                                   |
| `record_id`      | Required identifier referencing its source dataset                   |
| `result_id`      | Required unique identifier in `AN-nnnn` format                       |
| `scored_at`      | Required timestamp specified as UTC by the contract                  |
| `source_dataset` | Required value identifying the attendance or payroll feature dataset |

Additional implemented checks include identifier uniqueness, employee reference validation, allowed source-dataset values, and the requirement that attendance anomaly records have a null `money_at_risk`.

**Verification note:** The attendance `money_at_risk` rule has been implemented and tested against the current data. Full source-record existence validation remains unresolved because the relationship between anomaly `record_id` values and the loaded source records requires clarification. The timestamp's UTC designation also cannot be established from its data type alone.

### 6.2 AI Attrition Risk — `fact_attrition_risk`

**8 contract rules**

| Column                        | Requirement                                          |
| ----------------------------- | ---------------------------------------------------- |
| `as_of_date`                  | Required date; consistent within the defined batch   |
| `department_id`               | Required department reference                        |
| `employee_id`                 | Required employee reference; employee must be active |
| `model_version`               | Required model-version text                          |
| `prediction_id`               | Required unique identifier in `AR-nnnn` format       |
| `risk_band`                   | Required value of `Low`, `Medium`, or `High`         |
| `risk_score_12m`              | Required decimal value between 0 and 1               |
| `top_reason_1`–`top_reason_3` | Optional explanatory text                            |

Additional implemented checks include prediction identifier uniqueness, employee and department references, risk-band validation, score-range validation, and active-employee validation.

**Verification note:** The dataset contains records with two `as_of_date` values. Because the batch definition is not established, consistency across the entire table has not been enforced as a single-batch rule. This requirement needs clarification before final sign-off.

### 6.3 AI Forecast — `fact_forecast`

**9 contract rules**

| Column            | Requirement                                                       |
| ----------------- | ----------------------------------------------------------------- |
| `department_id`   | Required department identifier or `ALL`                           |
| `forecast_id`     | Required unique identifier in `FC-nnnn` format                    |
| `forecast_month`  | Required first day of the forecast month                          |
| `forecast_value`  | Required numeric value greater than or equal to zero              |
| `lower_80`        | Required lower bound, not greater than the forecast value         |
| `method`          | Required forecasting-method text                                  |
| `metric`          | Required value of `headcount_end` or `attrition_rate_monthly_pct` |
| `trained_through` | Required training cutoff in `YYYY-MM` format                      |
| `upper_80`        | Required upper bound, not less than the forecast value            |

Additional implemented checks include identifier uniqueness, identifier formats, valid department references, and date and numeric constraints.

### 6.4 Task Board — `fact_task`

**13 contract rules**

| Column                 | Requirement                                                                   |
| ---------------------- | ----------------------------------------------------------------------------- |
| `assignee_employee_id` | Required employee reference                                                   |
| `completed_date`       | Nullable; required for completed tasks and not earlier than `started_date`    |
| `created_date`         | Required date, not later than `started_date` when present                     |
| `due_date`             | Required date matching the sprint end date                                    |
| `priority`             | Required value from `P1`, `P2`, `P3`, or `P4`                                 |
| `reopened_count`       | Required integer greater than or equal to zero                                |
| `sprint_id`            | Required reference to a valid sprint                                          |
| `started_date`         | Nullable only when the task is `To Do`                                        |
| `status`               | Required value from `Done`, `In Progress`, `Blocked`, `To Do`, or `Cancelled` |
| `story_points`         | Required value from `1`, `2`, `3`, `5`, `8`, or `13`                          |
| `task_id`              | Required unique identifier in `TASK-nnnnn` format                             |
| `task_type`            | Required value from `Feature`, `Bug`, `Chore`, or `Spike`                     |
| `team_id`              | Required reference to a valid team                                            |

Additional implemented checks include employee, sprint, and team references; identifier uniqueness; allowed status and priority values; and date relationships.

## 7. Data Quality Pipeline

The `run_quality_pipeline.py` script processes the four contracted feeds.

The implemented validation checks cover applicable requirements such as:

* Required fields and nullability
* Identifier formats and uniqueness
* Numeric ranges and allowed values
* Date relationships and reporting periods
* Employee, department, sprint, and team references
* Selected cross-field business rules

The pipeline creates quarantine tables under the `quality` schema.

Rejected records are retained with a rejection reason rather than silently discarded. ETL audit statistics are recorded in `quality.etl_audit`.

**Important:** The 42-rule inventory has been retrieved from the contract table. This does not, by itself, prove that every rule is fully implemented in the pipeline. Final rule-by-rule verification is still required before claiming complete contract compliance.

## 8. Latest Verified Pipeline Results

The latest successful pipeline run produced these results:

| Feed                  | Rows Received | Rows Passed | Rows Quarantined |
| --------------------- | ------------: | ----------: | ---------------: |
| `fact_anomaly`        |           405 |         405 |                0 |
| `fact_attrition_risk` |           430 |         430 |                0 |
| `fact_forecast`       |            72 |          72 |                0 |
| `fact_task`           |        28,868 |      28,848 |               20 |
| **Total**             |    **29,775** |  **29,755** |           **20** |

The overall record pass rate was approximately **99.93%**.

These results reflect the latest recorded successful run and should be regenerated when the pipeline or source data changes.

## 9. Quarantined Records

The 20 quarantined task records were grouped as follows:

| Rejection Reason                            | Records |
| ------------------------------------------- | ------: |
| Completion date is before start date        |      12 |
| Task is Done but completion date is missing |       8 |
| **Total**                                   |  **20** |

The rejected rows were preserved in the task quarantine table with reasons to support investigation and correction.

## 10. Audit Logging and Repeatability

The `quality.etl_audit` table records the number of rows received, passed, and quarantined for each feed.

The pipeline has been rerun successfully, with consistent row counts in the latest verified results. Repeated runs may create additional audit entries.

## 11. Known Limitations and Outstanding Verification

The following items must be resolved or explicitly accepted before final production sign-off:

1. **Complete contract-to-code mapping:** Verify each of the 42 contract rules against the implemented validation logic and test evidence.
2. **Anomaly source-record mapping:** Clarify how anomaly `record_id` values map to the underlying attendance and payroll feature records.
3. **Timestamp timezone:** Establish how the `scored_at` UTC requirement is represented and verified.
4. **Attrition batch definition:** Clarify which records constitute a batch before enforcing a common `as_of_date`.
5. **Quarantine reason specificity:** Confirm that each rejection condition produces an informative reason rather than a generic message.
6. **Full pipeline coverage:** Confirm whether additional source tables require contracts and validation under PQ-01.

## 12. How to Run

Run these commands from the `05_Starter` directory with the project's virtual environment activated.

Load source data:

```powershell
python load_to_duckdb.py
```

Inspect the data contract inventory:

```powershell
python check_contract_coverage.py
```

Run the data quality pipeline:

```powershell
python run_quality_pipeline.py
```

Review audit statistics:

```powershell
python check_audit.py
```

Review quarantined records:

```powershell
python check_quarantine.py
```

## 13. Conclusion

PQ-01 has a working DuckDB loading process and a data quality pipeline for four contracted feeds. The implementation performs validation, retains rejected records with reasons, and records ETL audit statistics.

The contract inventory contains 42 rules. Full completion requires confirming the implementation and test evidence for each rule and resolving or documenting the outstanding limitations described above.
