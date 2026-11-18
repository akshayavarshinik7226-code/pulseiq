import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\nPULSEIQ - TASK QUARANTINE SUMMARY")
print("=" * 60)

summary = con.execute("""
    SELECT
        rejection_reason,
        COUNT(*) AS rejected_rows
    FROM quality.quarantine_fact_task
    GROUP BY rejection_reason
    ORDER BY rejected_rows DESC
""").fetchdf()

print(summary.to_string(index=False))

print("\nSample quarantined task records:")
print("-" * 60)

sample = con.execute("""
    SELECT
        task_id,
        status,
        started_date,
        completed_date,
        rejection_reason
    FROM quality.quarantine_fact_task
    ORDER BY task_id
    LIMIT 10
""").fetchdf()

print(sample.to_string(index=False))

con.close()