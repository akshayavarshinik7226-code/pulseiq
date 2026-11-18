import duckdb

con = duckdb.connect("pulseiq.duckdb")

query = """
WITH contract_tables AS (
SELECT
feed,
CASE
WHEN feed LIKE '%(fact_anomaly)%' THEN 'fact_anomaly'
WHEN feed LIKE '%(fact_attrition_risk)%' THEN 'fact_attrition_risk'
WHEN feed LIKE '%(fact_forecast)%' THEN 'fact_forecast'
WHEN feed LIKE '%(fact_task)%' THEN 'fact_task'
END AS table_name,
COUNT(*) AS contract_entries
FROM raw.data_contracts
GROUP BY feed
)
SELECT
ct.feed,
ct.table_name,
ct.contract_entries,
COUNT(DISTINCT c.column_name) AS contract_columns_found
FROM contract_tables AS ct
LEFT JOIN raw.data_contracts AS c
ON c.feed = ct.feed
LEFT JOIN information_schema.columns AS a
ON a.table_schema = 'raw'
AND a.table_name = ct.table_name
AND (
a.column_name = c.column_name
OR (
c.column_name = 'top_reason_1..3'
AND a.column_name IN (
'top_reason_1',
'top_reason_2',
'top_reason_3'
)
)
)
GROUP BY ct.feed, ct.table_name, ct.contract_entries
ORDER BY ct.feed
"""

print("PULSEIQ - CONTRACT COVERAGE")
print("=" * 60)
print(con.execute(query).fetchdf().to_string(index=False))

con.close()
