import duckdb

con = duckdb.connect("pulseiq.duckdb")

print("\n--- Prediction ID format ---")
print(
    con.execute("""
        SELECT prediction_id
        FROM raw.fact_attrition_risk
        WHERE prediction_id IS NULL
           OR NOT regexp_matches(prediction_id, '^AR-[0-9]{4}$')
    """).df().to_string(index=False)
)

print("\n--- Duplicate prediction IDs ---")
print(
    con.execute("""
        SELECT prediction_id, COUNT(*) AS occurrences
        FROM raw.fact_attrition_risk
        GROUP BY prediction_id
        HAVING COUNT(*) > 1
    """).df().to_string(index=False)
)

print("\n--- Attrition batch dates ---")
print(
    con.execute("""
        SELECT as_of_date, COUNT(*) AS records
        FROM raw.fact_attrition_risk
        GROUP BY as_of_date
        ORDER BY as_of_date
    """).df().to_string(index=False)
)

print("\n--- Employees without a current active record ---")
print(
    con.execute("""
        SELECT DISTINCT a.employee_id
        FROM raw.fact_attrition_risk a
        WHERE NOT EXISTS (
            SELECT 1
            FROM raw.dim_employee d
            WHERE d.employee_id = a.employee_id
              AND d.is_current = 'Y'
              AND d.employment_status = 'Active'
        )
    """).df().to_string(index=False)
)

con.close()