import duckdb

con = duckdb.connect("pulseiq.duckdb")

query = """
SELECT
    COUNT(*) AS total_rows,

    COUNT(*) FILTER (
        WHERE result_id IS NULL OR TRIM(result_id) = ''
    ) AS missing_result_id,

    COUNT(*) FILTER (
        WHERE employee_id IS NULL OR TRIM(employee_id) = ''
    ) AS missing_employee_id,

    COUNT(*) FILTER (
        WHERE anomaly_score IS NULL
           OR anomaly_score < 0
           OR anomaly_score > 1
    ) AS invalid_anomaly_score,

    COUNT(*) FILTER (
        WHERE flagged IS NULL
           OR flagged NOT IN ('Y', 'N')
    ) AS invalid_flagged_value,

    COUNT(*) FILTER (
        WHERE reason_code IS NULL OR TRIM(reason_code) = ''
    ) AS missing_reason_code,

    COUNT(*) FILTER (
        WHERE scored_at IS NULL
    ) AS missing_scored_at,

    COUNT(DISTINCT result_id) AS unique_result_ids,

    COUNT(*) FILTER (
        WHERE employee_id IS NOT NULL
          AND employee_id NOT IN (
              SELECT employee_id FROM raw.dim_employee
          )
    ) AS unknown_employee_ids

FROM raw.fact_anomaly
"""

print("PULSEIQ - ANOMALY DATA QUALITY CHECKS")
print("=" * 55)
print(con.execute(query).fetchdf().to_string(index=False))

con.close()