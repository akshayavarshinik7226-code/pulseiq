import duckdb

con = duckdb.connect("pulseiq.duckdb")

print("\n--- Attrition records with the earlier date ---")

print(
    con.execute("""
        SELECT
            prediction_id,
            employee_id,
            as_of_date,
            risk_score_12m,
            risk_band,
            model_version
        FROM raw.fact_attrition_risk
        WHERE as_of_date = DATE '2026-03-31'
        ORDER BY prediction_id
    """).df().to_string(index=False)
)

print("\n--- Records by date and model version ---")

print(
    con.execute("""
        SELECT
            as_of_date,
            model_version,
            COUNT(*) AS records
        FROM raw.fact_attrition_risk
        GROUP BY as_of_date, model_version
        ORDER BY as_of_date, model_version
    """).df().to_string(index=False)
)
print("\n--- Employee and department details by snapshot date ---")

print(
    con.execute("""
        SELECT
            a.as_of_date,
            COUNT(*) AS records,
            COUNT(DISTINCT a.employee_id) AS employees,
            COUNT(DISTINCT a.department_id) AS departments,
            MIN(a.prediction_id) AS first_prediction_id,
            MAX(a.prediction_id) AS last_prediction_id
        FROM raw.fact_attrition_risk a
        GROUP BY a.as_of_date
        ORDER BY a.as_of_date
    """).df().to_string(index=False)
)
con.close()