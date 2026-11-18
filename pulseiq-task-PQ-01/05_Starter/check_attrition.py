import duckdb

con = duckdb.connect("pulseiq.duckdb")

query = """
SELECT
    COUNT(*) AS total_rows,

    COUNT(*) FILTER (
        WHERE prediction_id IS NULL
           OR TRIM(prediction_id) = ''
    ) AS missing_prediction_id,

    COUNT(DISTINCT prediction_id) AS unique_prediction_ids,

    COUNT(*) FILTER (
        WHERE employee_id IS NULL
           OR TRIM(employee_id) = ''
    ) AS missing_employee_id,

    COUNT(*) FILTER (
        WHERE risk_score_12m IS NULL
           OR risk_score_12m < 0
           OR risk_score_12m > 1
    ) AS invalid_risk_score,

    COUNT(*) FILTER (
        WHERE risk_band IS NULL
           OR risk_band NOT IN ('Low', 'Medium', 'High')
    ) AS invalid_risk_band,

    COUNT(*) FILTER (
        WHERE department_id IS NULL
           OR TRIM(department_id) = ''
    ) AS missing_department_id,

    COUNT(*) FILTER (
        WHERE as_of_date IS NULL
    ) AS missing_as_of_date,

    COUNT(*) FILTER (
        WHERE model_version IS NULL
           OR TRIM(model_version) = ''
    ) AS missing_model_version,

    COUNT(*) FILTER (
        WHERE employee_id IS NOT NULL
          AND employee_id NOT IN (
              SELECT employee_id FROM raw.dim_employee
          )
    ) AS unknown_employee_ids,

    COUNT(*) FILTER (
        WHERE department_id IS NOT NULL
          AND department_id NOT IN (
              SELECT department_id FROM raw.dim_department
          )
    ) AS unknown_department_ids

FROM raw.fact_attrition_risk
"""

print("PULSEIQ - ATTRITION RISK DATA QUALITY CHECKS")
print("=" * 55)
print(con.execute(query).fetchdf().to_string(index=False))

con.close()