import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

checks = {
    "Created after start date": """
        SELECT COUNT(*)
        FROM raw.fact_task
        WHERE created_date > started_date
    """,
    "Due date differs from sprint end": """
        SELECT COUNT(*)
        FROM raw.fact_task t
        JOIN raw.dim_sprint s
          ON t.sprint_id = s.sprint_id
        WHERE t.due_date <> s.end_date
    """,
    "Invalid task type": """
        SELECT COUNT(*)
        FROM raw.fact_task
        WHERE task_type IS NULL
           OR task_type NOT IN ('Feature', 'Bug', 'Chore', 'Spike')
    """,
    "Invalid task ID format": """
        SELECT COUNT(*)
        FROM raw.fact_task
        WHERE NOT regexp_matches(task_id, '^TASK-[0-9]{5}$')
    """
}

print("\nPULSEIQ - TASK CONTRACT CHECKS")
print("=" * 45)

for name, sql in checks.items():
    count = con.execute(sql).fetchone()[0]
    print(f"{name}: {count}")

con.close()