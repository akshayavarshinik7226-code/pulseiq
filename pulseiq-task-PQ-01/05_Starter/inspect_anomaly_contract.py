import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

queries = {
    "Anomaly source datasets": """
        SELECT source_dataset, COUNT(*) AS row_count
        FROM raw.fact_anomaly
        GROUP BY source_dataset
        ORDER BY source_dataset
    """,
    "Anomaly reason codes": """
        SELECT reason_code, COUNT(*) AS row_count
        FROM raw.fact_anomaly
        GROUP BY reason_code
        ORDER BY reason_code
    """,
    "Anomaly period examples": """
        SELECT DISTINCT period
        FROM raw.fact_anomaly
        ORDER BY period
        LIMIT 12
    """,
    "Anomaly record ID examples": """
        SELECT record_id, source_dataset
        FROM raw.fact_anomaly
        LIMIT 10
    """,
}

for title, sql in queries.items():
    print(f"\n{title}")
    print("=" * 60)
    print(con.execute(sql).fetchdf().to_string(index=False))

con.close()