from pathlib import Path
import duckdb

DB_PATH = Path(__file__).resolve().parent / "pulseiq.duckdb"
con = duckdb.connect(str(DB_PATH))

print("PULSEIQ - DATA CONTRACT SUMMARY")
print("=" * 65)

result = con.execute("""
SELECT
feed,
COUNT(*) AS contract_columns
FROM raw.data_contracts
GROUP BY feed
ORDER BY feed
""").fetchdf()

print(result.to_string(index=False))

print("\nCONTRACT COLUMN DETAILS")
print("=" * 65)

details = con.execute("""
SELECT
feed,
column_name,
data_type,
nullable,
rule_or_allowed_values
FROM raw.data_contracts
ORDER BY feed, column_name
""").fetchdf()

print(details.to_string(index=False))

print("\nTotal contract rules:", len(details))

con.close()
