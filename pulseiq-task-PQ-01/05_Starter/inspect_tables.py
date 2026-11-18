import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

query = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'raw'
AND table_name = 'fact_attrition_risk'
ORDER BY ordinal_position
"""

results = con.execute(query).fetchdf()
print(results.to_string(index=False))

con.close()
