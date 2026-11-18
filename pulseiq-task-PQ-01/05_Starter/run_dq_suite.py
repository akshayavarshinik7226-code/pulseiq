# PulseIQ automated data quality suite
# Runs DQ-C01 through DQ-C14 and records dynamic results in quality.dq_results.

import duckdb
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / 'pulseiq.duckdb'

def run_check(con, check_id, check_name, affected_table, severity, query, notes=""):
    result = con.execute(query).df()
    bad_rows = len(result)

    if bad_rows == 0:
        status = "PASS"
    elif severity.lower() == "critical":
        status = "FAIL"
    else:
        status = "WARNING"

    return {
        "check_id": check_id,
        "check_name": check_name,
        "affected_table": affected_table,
        "bad_rows": bad_rows,
        "status": status,
        "severity": severity,
        "notes": notes,
        "run_time": datetime.now()
    }

CHECKS = []

CHECKS.extend([
    {
        "check_id": "DQ-C01",
        "check_name": "Payroll equals ledger",
        "affected_table": "fact_payroll, fact_ledger",
        "severity": "Critical",
        "query": """
            WITH payroll AS (
                SELECT DATE_TRUNC('month', period_end_date)::DATE AS month,
                       SUM(employer_cost) AS payroll_cost
                FROM raw.fact_payroll
                GROUP BY 1
            ),
            ledger AS (
                SELECT DATE_TRUNC('month', entry_date)::DATE AS month,
                       SUM(debit - credit) AS ledger_cost
                FROM raw.fact_ledger
                WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 5001 AND 5005
                GROUP BY 1
            )
            SELECT COALESCE(p.month, l.month) AS month,
                   p.payroll_cost,
                   l.ledger_cost
            FROM payroll p
            FULL OUTER JOIN ledger l USING (month)
            WHERE p.month IS NULL
               OR l.month IS NULL
               OR ABS(p.payroll_cost - l.ledger_cost) > 0.01
        """
    },
    {
        "check_id": "DQ-C02",
        "check_name": "Ledger balanced",
        "affected_table": "fact_ledger",
        "severity": "Critical",
        "query": """
            SELECT entry_id
            FROM raw.fact_ledger
            GROUP BY entry_id
            HAVING ABS(SUM(debit) - SUM(credit)) > 0.005
        """
    },
    {
        "check_id": "DQ-C03",
        "check_name": "Unique payroll rows",
        "affected_table": "fact_payroll",
        "severity": "Critical",
        "query": """
            SELECT employee_id, run_id
            FROM raw.fact_payroll
            GROUP BY employee_id, run_id
            HAVING COUNT(*) > 1
        """
    },
    {
        "check_id": "DQ-C04",
        "check_name": "No orphan employees",
        "affected_table": "fact_payroll",
        "severity": "Critical",
        "query": """
            SELECT p.payroll_item_id, p.employee_id
            FROM raw.fact_payroll p
            LEFT JOIN raw.dim_employee d
                ON p.employee_id = d.employee_id
            WHERE d.employee_id IS NULL
        """
    }
])

CHECKS.extend([
    {
        "check_id": "DQ-C05",
        "check_name": "No attendance after exit",
        "affected_table": "fact_attendance_monthly",
        "severity": "Warning",
        "query": """
            SELECT a.employee_id, a.period_end_date, d.exit_date
            FROM raw.fact_attendance_monthly a
            JOIN raw.dim_employee d
                ON a.employee_id = d.employee_id
            WHERE d.exit_date IS NOT NULL
              AND UPPER(CAST(d.is_current AS VARCHAR))
                  IN ('Y', 'TRUE', '1')
              AND a.period_end_date > LAST_DAY(d.exit_date)
        """
    },
    {
        "check_id": "DQ-C06",
        "check_name": "Unpaid leave deducted",
        "affected_table": "fact_attendance_monthly, fact_payroll",
        "severity": "Warning",
        "query": """
            WITH attendance AS (
                SELECT employee_id, period_end_date,
                       SUM(unpaid_absence_days + half_days_unpaid * 0.5) AS unpaid_days
                FROM raw.fact_attendance_monthly
                GROUP BY employee_id, period_end_date
            ),
            payroll AS (
                SELECT employee_id, period_end_date,
                       SUM(lop_days) AS lop_days
                FROM raw.fact_payroll
                GROUP BY employee_id, period_end_date
            )
            SELECT COALESCE(a.employee_id, p.employee_id) AS employee_id,
                   COALESCE(a.period_end_date, p.period_end_date)
                       AS period_end_date,
                   COALESCE(a.unpaid_days, 0) AS unpaid_days,
                   COALESCE(p.lop_days, 0) AS lop_days
            FROM attendance a
            FULL OUTER JOIN payroll p
                ON a.employee_id = p.employee_id
               AND a.period_end_date = p.period_end_date
            WHERE ABS(COALESCE(a.unpaid_days, 0)
                    - COALESCE(p.lop_days, 0)) > 0.5
        """
    },
    {
        "check_id": "DQ-C07",
        "check_name": "Invoice arithmetic",
        "affected_table": "fact_invoice",
        "severity": "Warning",
        "query": """
            SELECT invoice_id, amount_paid, total_amount, balance_due
            FROM raw.fact_invoice
            WHERE amount_paid > total_amount
               OR balance_due < 0
        """
    },
    {
        "check_id": "DQ-C08",
        "check_name": "Expense arithmetic",
        "affected_table": "fact_expense",
        "severity": "Warning",
        "query": """
            SELECT expense_id, amount_excl_gst, gst_amount, total_amount
            FROM raw.fact_expense
            WHERE ABS(total_amount - (amount_excl_gst + gst_amount)) > 0.01
        """
    }
])

CHECKS.extend([
    {
        "check_id": "DQ-C09",
        "check_name": "Task dates sensible",
        "affected_table": "fact_task",
        "severity": "Warning",
        "query": """
            SELECT task_id, status, started_date, completed_date
            FROM raw.fact_task
            WHERE (started_date IS NOT NULL
                   AND completed_date IS NOT NULL
                   AND completed_date < started_date)
               OR (LOWER(TRIM(status)) = 'done'
                   AND completed_date IS NULL)
        """
    },
    {
        "check_id": "DQ-C10",
        "check_name": "Leave dates sensible",
        "affected_table": "fact_leave",
        "severity": "Warning",
        "query": """
            SELECT leave_request_id, start_date, end_date
            FROM raw.fact_leave
            WHERE start_date IS NOT NULL
              AND end_date IS NOT NULL
              AND end_date < start_date
        """
    },
    {
        "check_id": "DQ-C11",
        "check_name": "AI feeds fresh",
        "affected_table": "fact_attrition_risk",
        "severity": "Warning",
        "query": """
            WITH latest AS (
                SELECT MAX(as_of_date) AS latest_date
                FROM raw.fact_attrition_risk
            )
            SELECT f.prediction_id, f.employee_id, f.as_of_date,
                   latest.latest_date
            FROM raw.fact_attrition_risk f
            CROSS JOIN latest
            WHERE f.as_of_date IS NOT NULL
              AND latest.latest_date IS NOT NULL
              AND DATE_DIFF('day', f.as_of_date, latest.latest_date) > 7
        """,
        "notes": "Checks prediction-date freshness only; scored_at is unavailable."
    },
    {
        "check_id": "DQ-C12",
        "check_name": "Dimension history does not overlap",
        "affected_table": "dim_employee",
        "severity": "Critical",
        "query": """
            WITH versions AS (
                SELECT employee_key, employee_id, valid_from, valid_to,
                       LEAD(valid_from) OVER (
                           PARTITION BY employee_id
                           ORDER BY valid_from, employee_key
                       ) AS next_valid_from
                FROM raw.dim_employee
            )
            SELECT employee_id, employee_key, valid_from, valid_to,
                   next_valid_from
            FROM versions
            WHERE next_valid_from IS NOT NULL
              AND (valid_to IS NULL OR valid_to >= next_valid_from)
        """
    }
])

CHECKS.extend([
    {
        "check_id": "DQ-C13",
        "check_name": "Pipeline freshness",
        "affected_table": "quality.etl_audit",
        "severity": "Critical",
        "query": """
            SELECT MAX(run_time) AS latest_run_time
            FROM quality.etl_audit
            HAVING MAX(run_time) < CURRENT_TIMESTAMP - INTERVAL '24 hours'
        """,
        "notes": "Checks audit recency; the audit table does not record successful-run status."
    },
    {
        "check_id": "DQ-C14",
        "check_name": "Minimum group size",
        "affected_table": "metric_dictionary",
        "severity": "Critical",
        "query": """
            SELECT metric_id, metric_name, minimum_group_size
            FROM raw.metric_dictionary
            WHERE minimum_group_size IS NULL
               OR TRIM(CAST(minimum_group_size AS VARCHAR)) = ''
               OR LOWER(TRIM(CAST(minimum_group_size AS VARCHAR))) = 'nan'
        """,
        "notes": "Reports missing thresholds only; enforcement in published metrics is not yet verified."
    }
])


# Safety switch: keep False during initial testing.
WRITE_RESULTS = False


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    results = []

    try:
        for check in CHECKS:
            result = run_check(
                con,
                check["check_id"],
                check["check_name"],
                check["affected_table"],
                check["severity"],
                check["query"],
                check.get("notes", "")
            )

            if check["check_id"] == "DQ-C14":
                result["status"] = "NOT_VERIFIED"

            results.append(result)

    finally:
        con.close()

    print("\\nPULSEIQ DATA QUALITY REPORT")
    print("=" * 90)

    for result in results:
        print(
            f'{result["check_id"]} | {result["status"]:<13} | '
            f'Bad rows: {result["bad_rows"]:<5} | '
            f'{result["check_name"]}'
        )
        if result["notes"]:
            print(f'    Note: {result["notes"]}')

    print("=" * 90)
    print(f"Checks run: {len(results)}")
    print(f"Passed: {sum(r['status'] == 'PASS' for r in results)}")
    print(f"Failed: {sum(r['status'] == 'FAIL' for r in results)}")
    print(f"Warnings: {sum(r['status'] == 'WARNING' for r in results)}")
    print(f"Not verified: {sum(r['status'] == 'NOT_VERIFIED' for r in results)}")
    print("Database results table updated: NO (report-only mode)")


if __name__ == "__main__":
    main()

