import duckdb

con = duckdb.connect("pulseiq.duckdb")

print("\n--- Data dictionary entries for attrition risk ---")

print(
    con.execute("""
        SELECT *
        FROM raw.data_dictionary
        WHERE sheet = 'fact_attrition_risk'
    """).df().to_string(index=False)
)

print("\n--- Known data-quality issues ---")

print(
    con.execute("""
        SELECT *
        FROM raw.data_dictionary
        WHERE sheet = 'dq_known_issues'
    """).df().to_string(index=False)
)

con.close()