import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\nPULSEIQ - OFFICIAL DATA CONTRACTS")
print("=" * 70)

contracts = con.execute("""
    SELECT
        feed,
        column_name,
        data_type,
        nullable,
        rule_or_allowed_values
    FROM raw.data_contracts
    ORDER BY feed, column_name
""").fetchdf()

print(contracts.to_string(index=False))

print("\nCONTRACT COUNTS BY FEED")
print("=" * 70)

summary = con.execute("""
    SELECT
        feed,
        COUNT(*) AS contract_rules
    FROM raw.data_contracts
    GROUP BY feed
    ORDER BY feed
""").fetchdf()

print(summary.to_string(index=False))

con.close()