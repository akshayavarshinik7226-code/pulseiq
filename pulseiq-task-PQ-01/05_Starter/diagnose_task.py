import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

# Check tasks with completion dates before start dates
invalid_dates = con.execute("""
    SELECT COUNT(*)
    FROM raw.fact_task
    WHERE completed_date < started_date
""").fetchone()[0]

# Check tasks marked Done without a completion date
missing_completion = con.execute("""
    SELECT COUNT(*)
    FROM raw.fact_task
    WHERE status = 'Done'
      AND completed_date IS NULL
""").fetchone()[0]

# Check the current quarantine table
quarantined = con.execute("""
    SELECT COUNT(*)
    FROM quality.quarantine_fact_task
""").fetchone()[0]

print("TASK DATA DIAGNOSTIC")
print("--------------------")
print(f"Completion before start date: {invalid_dates}")
print(f"Done without completion date: {missing_completion}")
print(f"Currently quarantined:        {quarantined}")

con.close()