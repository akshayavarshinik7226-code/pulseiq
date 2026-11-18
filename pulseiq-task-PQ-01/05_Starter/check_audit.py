import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\nPULSEIQ - ETL AUDIT SUMMARY")
print("=" * 65)

results = con.execute("""
    SELECT
        table_name,
        rows_received,
        rows_passed,
        rows_quarantined
    FROM quality.etl_audit
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY table_name
        ORDER BY run_time DESC
    ) = 1
    ORDER BY table_name
""").fetchdf()

print(results.to_string(index=False))
print("\nNumber of feeds:", len(results))

con.close()