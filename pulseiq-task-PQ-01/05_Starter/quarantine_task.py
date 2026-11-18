import duckdb

con = duckdb.connect("pulseiq.duckdb")

# Create a schema for rejected records and audit summaries.
con.execute("CREATE SCHEMA IF NOT EXISTS quality")

# Create a quarantine table with the original task data
# and a column explaining why the row was rejected.
con.execute("""
CREATE TABLE IF NOT EXISTS quality.quarantine_task AS
SELECT
    *,
    CAST(NULL AS VARCHAR) AS rejection_reason
FROM raw.fact_task
WHERE FALSE
""")

# Create an audit table to track each run.
con.execute("""
CREATE TABLE IF NOT EXISTS quality.etl_audit (
    table_name VARCHAR,
    rows_received BIGINT,
    rows_passed BIGINT,
    rows_quarantined BIGINT,
    run_time TIMESTAMP
)
""")

# Start with a clean quarantine for this table so reruns
# don't duplicate previously quarantined records.
con.execute("DELETE FROM quality.quarantine_task")

# Identify invalid task rows and save their rejection reasons.
con.execute("""
INSERT INTO quality.quarantine_task
SELECT
    *,
    CASE
        WHEN completed_date IS NOT NULL
             AND started_date IS NOT NULL
             AND completed_date < started_date
             AND status = 'Done'
        THEN 'Completion date is before start date'

        WHEN status = 'Done'
             AND completed_date IS NULL
        THEN 'Task is Done but completion date is missing'

        WHEN completed_date IS NOT NULL
             AND started_date IS NOT NULL
             AND completed_date < started_date
        THEN 'Completion date is before start date'
    END AS rejection_reason
FROM raw.fact_task
WHERE
    (
        completed_date IS NOT NULL
        AND started_date IS NOT NULL
        AND completed_date < started_date
    )
    OR
    (
        status = 'Done'
        AND completed_date IS NULL
    )
""")

# Count incoming and rejected records.
rows_received = con.execute("""
SELECT COUNT(*) FROM raw.fact_task
""").fetchone()[0]

rows_quarantined = con.execute("""
SELECT COUNT(*) FROM quality.quarantine_task
""").fetchone()[0]

rows_passed = rows_received - rows_quarantined

# Record the run's results.
con.execute("""
INSERT INTO quality.etl_audit
VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
""", [
    "fact_task",
    rows_received,
    rows_passed,
    rows_quarantined
])

# Show the audit summary.
print("PULSEIQ - TASK ETL AUDIT")
print("=" * 60)

print(con.execute("""
SELECT
    table_name,
    rows_received,
    rows_passed,
    rows_quarantined,
    run_time
FROM quality.etl_audit
ORDER BY run_time DESC
LIMIT 1
""").fetchdf().to_string(index=False))

print("\nQUARANTINE REASONS")
print("=" * 60)

print(con.execute("""
SELECT
    rejection_reason,
    COUNT(*) AS rejected_rows
FROM quality.quarantine_task
GROUP BY rejection_reason
ORDER BY rejection_reason
""").fetchdf().to_string(index=False))

con.close()