import duckdb

con = duckdb.connect("pulseiq.duckdb")

query = """
SELECT
    COUNT(*) AS total_rows,

    COUNT(*) FILTER (
        WHERE task_id IS NULL
           OR TRIM(task_id) = ''
    ) AS missing_task_id,

    COUNT(DISTINCT task_id) AS unique_task_ids,

    COUNT(*) FILTER (
        WHERE assignee_employee_id IS NULL
           OR TRIM(assignee_employee_id) = ''
    ) AS missing_assignee,

    COUNT(*) FILTER (
        WHERE status IS NULL
           OR status NOT IN (
               'Done', 'In Progress', 'Blocked',
               'To Do', 'Cancelled'
           )
    ) AS invalid_status,

    COUNT(*) FILTER (
        WHERE priority IS NULL
           OR priority NOT IN ('P1', 'P2', 'P3', 'P4')
    ) AS invalid_priority,

    COUNT(*) FILTER (
        WHERE story_points IS NULL
           OR story_points NOT IN (1, 2, 3, 5, 8, 13)
    ) AS invalid_story_points,

    COUNT(*) FILTER (
        WHERE reopened_count IS NULL
           OR reopened_count < 0
    ) AS invalid_reopened_count,

    COUNT(*) FILTER (
        WHERE created_date IS NULL
    ) AS missing_created_date,

    COUNT(*) FILTER (
        WHERE completed_date IS NOT NULL
          AND completed_date < started_date
    ) AS completion_before_start,

    COUNT(*) FILTER (
        WHERE status = 'Done'
          AND completed_date IS NULL
    ) AS done_without_completion_date,

    COUNT(*) FILTER (
        WHERE started_date IS NULL
          AND status <> 'To Do'
    ) AS missing_start_date,

    COUNT(*) FILTER (
        WHERE assignee_employee_id IS NOT NULL
          AND assignee_employee_id NOT IN (
              SELECT employee_id FROM raw.dim_employee
          )
    ) AS unknown_assignees,

    COUNT(*) FILTER (
        WHERE sprint_id IS NOT NULL
          AND sprint_id NOT IN (
              SELECT sprint_id FROM raw.dim_sprint
          )
    ) AS unknown_sprints,

    COUNT(*) FILTER (
        WHERE team_id IS NOT NULL
          AND team_id NOT IN (
              SELECT team_id FROM raw.dim_team
          )
    ) AS unknown_teams

FROM raw.fact_task
"""

print("PULSEIQ - TASK DATA QUALITY CHECKS")
print("=" * 55)
print(con.execute(query).fetchdf().to_string(index=False))

con.close()