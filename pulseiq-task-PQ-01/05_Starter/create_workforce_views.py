from pathlib import Path
import duckdb

DB_PATH = Path("C:/Users/Kishore/Downloads/project/05_Starter/pulseiq.duckdb")
con = duckdb.connect(str(DB_PATH))

con.execute("""
CREATE OR REPLACE VIEW m29_location_tier AS
SELECT
l.city_tier AS tier_name,
COUNT(DISTINCT e.employee_id) AS employees
FROM warehouse.dim_employee AS e
JOIN warehouse.dim_location AS l
ON e.work_location = l.work_location
WHERE e.is_current = 'Y'
AND e.employment_status = 'Active'
AND l.city_tier IS NOT NULL
GROUP BY l.city_tier
""")

con.execute("""
CREATE OR REPLACE VIEW m30_work_mode AS
SELECT
work_mode,
COUNT(DISTINCT employee_id) AS employees
FROM warehouse.dim_employee
WHERE is_current = 'Y'
AND employment_status = 'Active'
AND work_mode IS NOT NULL
GROUP BY work_mode
""")

print("Location-tier view:")
print(con.execute(
"SELECT * FROM m29_location_tier ORDER BY tier_name"
).fetchdf().to_string(index=False))

print("\nWork-mode view:")
print(con.execute(
"SELECT * FROM m30_work_mode ORDER BY employees DESC"
).fetchdf().to_string(index=False))

con.close()
