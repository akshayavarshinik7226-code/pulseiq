import duckdb

con = duckdb.connect("pulseiq.duckdb")

print("\n--- Anomaly rejection reasons ---")
print(
    con.execute("""
        SELECT rejection_reason, COUNT(*) AS rejected_rows
        FROM quality.quarantine_fact_anomaly
        GROUP BY rejection_reason
        ORDER BY rejected_rows DESC
    """).df().to_string(index=False)
)

print("\n--- Check record ID formats ---")
print(
    con.execute("""
        SELECT record_id, COUNT(*) AS total
        FROM raw.fact_anomaly
        WHERE NOT regexp_matches(record_id, '^AF-[0-9]{5}$')
        GROUP BY record_id
        LIMIT 10
    """).df().to_string(index=False)
)

print("\n--- Check reason codes ---")
print(
    con.execute("""
        SELECT reason_code, COUNT(*) AS total
        FROM raw.fact_anomaly
        GROUP BY reason_code
        ORDER BY total DESC
    """).df().to_string(index=False)
)

print("\n--- Check source datasets ---")
print(
    con.execute("""
        SELECT source_dataset, COUNT(*) AS total
        FROM raw.fact_anomaly
        GROUP BY source_dataset
        ORDER BY total DESC
    """).df().to_string(index=False)
)

con.close()