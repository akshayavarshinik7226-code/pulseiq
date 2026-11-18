from pathlib import Path
import duckdb

DB_PATH = Path(__file__).resolve().parent / "pulseiq.duckdb"
con = duckdb.connect(str(DB_PATH))

con.execute("CREATE SCHEMA IF NOT EXISTS quality")

# Store audit results for each feed and run.
con.execute("""
CREATE TABLE IF NOT EXISTS quality.etl_audit (
    table_name VARCHAR,
    rows_received BIGINT,
    rows_passed BIGINT,
    rows_quarantined BIGINT,
    run_time TIMESTAMP
)
""")

# Rules implemented so far for each contracted feed.
checks = {
            "fact_anomaly": """
        result_id IS NULL
        OR TRIM(result_id) = ''
        OR NOT regexp_matches(result_id, '^AN-[0-9]{4}$')

        OR employee_id IS NULL
        OR TRIM(employee_id) = ''

        OR anomaly_score IS NULL
        OR anomaly_score < 0
        OR anomaly_score > 1

        OR flagged IS NULL
        OR flagged NOT IN ('Y', 'N')

        OR model_version IS NULL
        OR TRIM(model_version) = ''

        OR period IS NULL
        OR (
            period IS NOT NULL
            AND EXTRACT(DAY FROM period) <> 1
            AND period <> last_day(period)
        )

        OR reason_code IS NULL
        OR TRIM(reason_code) = ''
        OR reason_code NOT IN (
            'FREQUENT_LATE',
            'GROSS_ABOVE_NORM',
            'GROSS_BELOW_EXPECTED',
            'LONG_UNPAID_ABSENCE',
            'NEGATIVE_NET_PAY',
            'NO_ATTENDANCE',
            'OVERTIME_ABOVE_CAP',
            'PATTERN_SHIFT',
            'PF_NOT_DEDUCTED',
            'STATISTICAL_OUTLIER',
            'ZERO_PAY'
        )

        OR reason_text IS NULL
        OR TRIM(reason_text) = ''

       OR record_id IS NULL
OR TRIM(record_id) = ''
OR (
    source_dataset = 'attendance_monthly_features'
    AND NOT regexp_matches(record_id, '^AF-[0-9]{5}$')
)
OR (
    source_dataset = 'payroll_monthly_features'
    AND NOT regexp_matches(record_id, '^PI-[0-9]{6}$')
)
        OR source_dataset IS NULL
        OR source_dataset NOT IN (
            'attendance_monthly_features',
            'payroll_monthly_features'
        )
        OR (
    source_dataset = 'attendance_monthly_features'
    AND money_at_risk IS NOT NULL
)

        OR scored_at IS NULL

        OR employee_id NOT IN (
            SELECT employee_id FROM raw.dim_employee
        )

        OR result_id IN (
            SELECT result_id
            FROM raw.fact_anomaly
            GROUP BY result_id
            HAVING COUNT(*) > 1
        )
    """,
        "fact_attrition_risk": """
        prediction_id IS NULL
        OR TRIM(prediction_id) = ''
        OR NOT regexp_matches(prediction_id, '^AR-[0-9]{4}$')

        OR employee_id IS NULL
        OR TRIM(employee_id) = ''

        OR risk_score_12m IS NULL
        OR risk_score_12m < 0
        OR risk_score_12m > 1

        OR risk_band IS NULL
        OR risk_band NOT IN ('Low', 'Medium', 'High')

        OR department_id IS NULL
        OR TRIM(department_id) = ''

        OR as_of_date IS NULL

        OR model_version IS NULL
        OR TRIM(model_version) = ''

        OR employee_id NOT IN (
            SELECT employee_id
            FROM raw.dim_employee
        )

        OR department_id NOT IN (
            SELECT department_id
            FROM raw.dim_department
        )

        OR NOT EXISTS (
            SELECT 1
            FROM raw.dim_employee d
            WHERE d.employee_id = raw.fact_attrition_risk.employee_id
              AND d.is_current = 'Y'
              AND d.employment_status = 'Active'
        )

        OR prediction_id IN (
            SELECT prediction_id
            FROM raw.fact_attrition_risk
            GROUP BY prediction_id
            HAVING COUNT(*) > 1
        )

        OR (
            top_reason_1 IS NOT NULL
            AND TRIM(top_reason_1) = ''
        )

        OR (
            top_reason_2 IS NOT NULL
            AND TRIM(top_reason_2) = ''
        )

        OR (
            top_reason_3 IS NOT NULL
            AND TRIM(top_reason_3) = ''
        )
    """,
                "fact_forecast": """
        forecast_id IS NULL
        OR TRIM(forecast_id) = ''
        OR NOT regexp_matches(forecast_id, '^FC-[0-9]{4}$')

        OR forecast_value IS NULL
        OR forecast_value < 0

        OR lower_80 IS NULL
        OR lower_80 > forecast_value

        OR upper_80 IS NULL
        OR upper_80 < forecast_value

        OR metric IS NULL
        OR metric NOT IN (
            'headcount_end',
            'attrition_rate_monthly_pct'
        )

        OR department_id IS NULL
        OR TRIM(department_id) = ''
        OR (
            department_id <> 'ALL'
            AND department_id NOT IN (
                SELECT department_id FROM raw.dim_department
            )
        )

        OR forecast_month IS NULL
        OR EXTRACT(DAY FROM forecast_month) <> 1

        OR method IS NULL
        OR TRIM(method) = ''

        OR trained_through IS NULL
        OR NOT regexp_matches(
            trained_through, '^[0-9]{4}-(0[1-9]|1[0-2])$'
        )

        OR forecast_id IN (
            SELECT forecast_id
            FROM raw.fact_forecast
            GROUP BY forecast_id
            HAVING COUNT(*) > 1
        )
    """,
    "fact_task": """
        task_id IS NULL
        OR TRIM(task_id) = ''

        OR assignee_employee_id IS NULL
        OR TRIM(assignee_employee_id) = ''

        OR status IS NULL
        OR status NOT IN (
            'Done', 'In Progress', 'Blocked', 'To Do', 'Cancelled'
        )

        OR priority IS NULL
        OR priority NOT IN ('P1', 'P2', 'P3', 'P4')

        OR story_points IS NULL
        OR story_points NOT IN (1, 2, 3, 5, 8, 13)

        OR reopened_count IS NULL
        OR reopened_count < 0

        OR created_date IS NULL

        OR (
            created_date IS NOT NULL
            AND started_date IS NOT NULL
            AND created_date > started_date
        )

        OR (
            completed_date IS NOT NULL
            AND started_date IS NOT NULL
            AND completed_date < started_date
        )

        OR (
            status = 'Done'
            AND completed_date IS NULL
        )

        OR (
            started_date IS NULL
            AND status <> 'To Do'
        )

        OR assignee_employee_id NOT IN (
            SELECT employee_id FROM raw.dim_employee
        )

        OR sprint_id NOT IN (
            SELECT sprint_id FROM raw.dim_sprint
        )

        OR team_id NOT IN (
            SELECT team_id FROM raw.dim_team
        )

        OR task_type IS NULL
        OR task_type NOT IN ('Feature', 'Bug', 'Chore', 'Spike')

        OR due_date IS NULL
        OR due_date <> (
            SELECT end_date
            FROM raw.dim_sprint
            WHERE dim_sprint.sprint_id = fact_task.sprint_id
        )

        OR NOT regexp_matches(task_id, '^TASK-[0-9]{5}$')

        OR task_id IN (
            SELECT task_id
            FROM raw.fact_task
            GROUP BY task_id
            HAVING COUNT(*) > 1
        )
    """
}

for table_name, invalid_condition in checks.items():
    quarantine_table = "quarantine_" + table_name

    # Create a quarantine table containing source columns and a reason.
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS quality.{quarantine_table} AS
        SELECT *, CAST(NULL AS VARCHAR) AS rejection_reason
        FROM raw.{table_name}
        WHERE FALSE
    """)

    # Refresh quarantine on each run, avoiding duplicate rejected rows.
    con.execute(f"DELETE FROM quality.{quarantine_table}")

    # Keep the raw source unchanged.
    if table_name == "fact_task":
        reason_expression = """
            CASE
                WHEN task_id IS NULL OR TRIM(task_id) = ''
                    THEN 'Missing task ID'

                WHEN completed_date IS NOT NULL
                     AND started_date IS NOT NULL
                     AND completed_date < started_date
                    THEN 'Completion date is before start date'

                WHEN status = 'Done'
                     AND completed_date IS NULL
                    THEN 'Task is Done but completion date is missing'

                WHEN started_date IS NULL
                     AND status <> 'To Do'
                    THEN 'Missing start date for task status'

                WHEN assignee_employee_id IS NULL
                     OR TRIM(assignee_employee_id) = ''
                    THEN 'Missing assignee employee ID'

                WHEN assignee_employee_id NOT IN (
                    SELECT employee_id FROM raw.dim_employee
                )
                    THEN 'Assignee employee ID not found'

                WHEN sprint_id NOT IN (
                    SELECT sprint_id FROM raw.dim_sprint
                )
                    THEN 'Sprint ID not found'

                WHEN team_id NOT IN (
                    SELECT team_id FROM raw.dim_team
                )
                    THEN 'Team ID not found'

                WHEN status NOT IN (
                    'Done', 'In Progress', 'Blocked', 'To Do', 'Cancelled'
                ) OR status IS NULL
                    THEN 'Invalid task status'

                WHEN priority NOT IN ('P1', 'P2', 'P3', 'P4')
                     OR priority IS NULL
                    THEN 'Invalid priority'

                WHEN story_points NOT IN (1, 2, 3, 5, 8, 13)
                     OR story_points IS NULL
                    THEN 'Invalid story points'

                WHEN reopened_count IS NULL OR reopened_count < 0
                    THEN 'Invalid reopened count'

                WHEN created_date IS NULL
                    THEN 'Missing creation date'

                ELSE 'Multiple contract checks failed'
            END
        """
    elif table_name == "fact_anomaly":
        reason_expression = """
            CASE
                WHEN result_id IS NULL OR TRIM(result_id) = ''
                    THEN 'Missing result ID'
                WHEN employee_id IS NULL OR TRIM(employee_id) = ''
                    THEN 'Missing employee ID'
                WHEN anomaly_score IS NULL
                     OR anomaly_score < 0 OR anomaly_score > 1
                    THEN 'Anomaly score outside 0 to 1'
                WHEN flagged IS NULL OR flagged NOT IN ('Y', 'N')
                    THEN 'Invalid flagged value'
                WHEN scored_at IS NULL
                    THEN 'Missing scoring timestamp'
                WHEN employee_id NOT IN (
                    SELECT employee_id FROM raw.dim_employee
                )
                    THEN 'Employee ID not found'
                ELSE 'Multiple contract checks failed'
            END
        """
    
    elif table_name == "fact_forecast":
     reason_expression = """
        CASE
            WHEN forecast_id IS NULL OR TRIM(forecast_id) = ''
                THEN 'Missing forecast ID'
            WHEN NOT regexp_matches(forecast_id, '^FC-[0-9]{4}$')
                THEN 'Invalid forecast ID format'
            WHEN forecast_id IN (
                SELECT forecast_id
                FROM raw.fact_forecast
                GROUP BY forecast_id
                HAVING COUNT(*) > 1
            )
                THEN 'Duplicate forecast ID'
            WHEN forecast_value IS NULL OR forecast_value < 0
                THEN 'Invalid forecast value'
            WHEN lower_80 IS NULL OR lower_80 > forecast_value
                THEN 'Invalid lower forecast bound'
            WHEN upper_80 IS NULL OR upper_80 < forecast_value
                THEN 'Invalid upper forecast bound'
            WHEN metric IS NULL OR metric NOT IN (
                'headcount_end', 'attrition_rate_monthly_pct'
            )
                THEN 'Invalid forecast metric'
            WHEN department_id IS NULL OR TRIM(department_id) = ''
                THEN 'Missing department ID'
            WHEN department_id <> 'ALL'
                 AND department_id NOT IN (
                     SELECT department_id
                     FROM raw.dim_department
                 )
                THEN 'Department ID not found'
            WHEN forecast_month IS NULL
                 OR EXTRACT(DAY FROM forecast_month) <> 1
                THEN 'Forecast month must be the first day of the month'
            WHEN method IS NULL OR TRIM(method) = ''
                THEN 'Missing forecast method'
            WHEN trained_through IS NULL
                 OR NOT regexp_matches(
                     trained_through, '^[0-9]{4}-(0[1-9]|1[0-2])$'
                 )
                THEN 'Invalid trained_through format; expected YYYY-MM'
            ELSE 'Multiple contract checks failed'
        END
    """


    else:
        reason_expression = """
            CASE
                WHEN prediction_id IS NULL OR TRIM(prediction_id) = ''
                    THEN 'Missing prediction ID'
                WHEN employee_id IS NULL OR TRIM(employee_id) = ''
                    THEN 'Missing employee ID'
                WHEN risk_score_12m IS NULL
                     OR risk_score_12m < 0 OR risk_score_12m > 1
                    THEN 'Risk score outside 0 to 1'
                WHEN risk_band IS NULL OR risk_band NOT IN (
                    'Low', 'Medium', 'High'
                )
                    THEN 'Invalid risk band'
                WHEN employee_id NOT IN (
                    SELECT employee_id FROM raw.dim_employee
                )
                    THEN 'Employee ID not found'
                WHEN department_id NOT IN (
                    SELECT department_id FROM raw.dim_department
                )
                    THEN 'Department ID not found'
                ELSE 'Multiple contract checks failed'
            END
            """

    # Insert rejected rows into the quarantine table.
    con.execute(f"""
        INSERT INTO quality.{quarantine_table}
        SELECT *, {reason_expression} AS rejection_reason
        FROM raw.{table_name}
        WHERE {invalid_condition}
    """)

    received = con.execute(
        f"SELECT COUNT(*) FROM raw.{table_name}"
    ).fetchone()[0]

    rejected = con.execute(
        f"SELECT COUNT(*) FROM quality.{quarantine_table}"
    ).fetchone()[0]

    passed = received - rejected

    con.execute("""
        INSERT INTO quality.etl_audit
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, [table_name, received, passed, rejected])

    print(
        f"{table_name:<25} "
        f"received={received:>6} "
        f"passed={passed:>6} "
        f"quarantined={rejected:>4}"
    )

con.close()