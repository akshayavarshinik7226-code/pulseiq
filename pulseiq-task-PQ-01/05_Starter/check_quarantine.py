import duckdb

con = duckdb.connect("pulseiq.duckdb")

print("PULSEIQ - TASK QUARANTINE SUMMARY")
print("=" * 55)

result = con.execute("""
SELECT
rejection_reason,
COUNT(*) AS rejected_rows
FROM quality.quarantine_fact_task
GROUP BY rejection_reason
ORDER BY rejected_rows DESC
""").fetchdf()

print(result.to_string(index=False))

total = con.execute("""
SELECT COUNT(*)
FROM quality.quarantine_fact_task
""").fetchone()[0]

print("\nTotal quarantined task rows:", total)

con.close()
