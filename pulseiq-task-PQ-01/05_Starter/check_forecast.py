import duckdb

con = duckdb.connect("pulseiq.duckdb")

query = """
SELECT
    COUNT(*) AS total_rows,

    COUNT(*) FILTER (
        WHERE forecast_id IS NULL
           OR TRIM(forecast_id) = ''
    ) AS missing_forecast_id,

    COUNT(DISTINCT forecast_id) AS unique_forecast_ids,

    COUNT(*) FILTER (
        WHERE forecast_value IS NULL
           OR forecast_value < 0
    ) AS invalid_forecast_value,

    COUNT(*) FILTER (
        WHERE lower_80 IS NULL
           OR lower_80 > forecast_value
    ) AS invalid_lower_bound,

    COUNT(*) FILTER (
        WHERE upper_80 IS NULL
           OR upper_80 < forecast_value
    ) AS invalid_upper_bound,

    COUNT(*) FILTER (
        WHERE metric NOT IN (
            'headcount_end',
            'attrition_rate_monthly_pct'
        )
        OR metric IS NULL
    ) AS invalid_metric,

    COUNT(*) FILTER (
        WHERE department_id IS NULL
           OR TRIM(department_id) = ''
    ) AS missing_department_id,

    COUNT(*) FILTER (
        WHERE forecast_month IS NULL
           OR EXTRACT(DAY FROM forecast_month) <> 1
    ) AS invalid_forecast_month,

    COUNT(*) FILTER (
        WHERE method IS NULL
           OR TRIM(method) = ''
    ) AS missing_method

FROM raw.fact_forecast
"""

print("PULSEIQ - FORECAST DATA QUALITY CHECKS")
print("=" * 55)
print(con.execute(query).fetchdf().to_string(index=False))

con.close()