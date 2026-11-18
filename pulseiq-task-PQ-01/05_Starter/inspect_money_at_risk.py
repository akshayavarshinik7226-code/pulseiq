import duckdb

con = duckdb.connect("pulseiq.duckdb")

print("MONEY_AT_RISK BY SOURCE DATASET")
print("=" * 55)

result = con.execute("""
SELECT
source_dataset,
COUNT(*) AS total_rows,
COUNT(money_at_risk) AS non_null_money_at_risk,
SUM(CASE WHEN money_at_risk IS NULL THEN 1 ELSE 0 END)
AS null_money_at_risk
FROM raw.fact_anomaly
GROUP BY source_dataset
ORDER BY source_dataset
""").fetchdf()

print(result.to_string(index=False))

print("\nSAMPLE ATTENDANCE RECORDS WITH MONEY_AT_RISK")
print("=" * 55)

sample = con.execute("""
SELECT result_id, source_dataset, money_at_risk
FROM raw.fact_anomaly
WHERE source_dataset = 'attendance_monthly_features'
AND money_at_risk IS NOT NULL
LIMIT 10
""").fetchdf()

if sample.empty:
    print("No attendance records have a non-null money_at_risk value.")
else:
    print(sample.to_string(index=False))

con.close()
