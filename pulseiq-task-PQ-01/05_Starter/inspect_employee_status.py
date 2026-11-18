import duckdb

con = duckdb.connect("pulseiq.duckdb")

print("\n--- Employee dimension columns ---")
print(
    con.execute("""
        DESCRIBE raw.dim_employee
    """).df().to_string(index=False)
)

print("\n--- Sample employee records ---")
print(
    con.execute("""
        SELECT *
        FROM raw.dim_employee
        LIMIT 5
    """).df().to_string(index=False)
)

con.close()