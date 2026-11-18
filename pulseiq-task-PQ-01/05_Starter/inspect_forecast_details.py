import duckdb

con = duckdb.connect("pulseiq.duckdb")

print("\n--- Forecast ID format ---")
print(
    con.execute("""
        SELECT forecast_id
        FROM raw.fact_forecast
        WHERE forecast_id IS NULL
           OR NOT regexp_matches(forecast_id, '^FC-[0-9]{4}$')
    """).df().to_string(index=False)
)

print("\n--- Duplicate forecast IDs ---")
print(
    con.execute("""
        SELECT forecast_id, COUNT(*) AS occurrences
        FROM raw.fact_forecast
        GROUP BY forecast_id
        HAVING COUNT(*) > 1
    """).df().to_string(index=False)
)

print("\n--- Forecast department IDs ---")
print(
    con.execute("""
        SELECT DISTINCT f.department_id
        FROM raw.fact_forecast f
        WHERE f.department_id IS NULL
           OR (
               f.department_id <> 'ALL'
               AND NOT EXISTS (
                   SELECT 1
                   FROM raw.dim_department d
                   WHERE d.department_id = f.department_id
               )
           )
    """).df().to_string(index=False)
)

print("\n--- trained_through format ---")
print(
    con.execute("""
        SELECT DISTINCT trained_through
        FROM raw.fact_forecast
        WHERE trained_through IS NULL
           OR NOT regexp_matches(trained_through, '^[0-9]{4}-[0-9]{2}$')
           OR TRY_CAST(trained_through || '-01' AS DATE) IS NULL
        ORDER BY trained_through
    """).df().to_string(index=False)
)

con.close()