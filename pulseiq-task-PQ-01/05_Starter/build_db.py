from pathlib import Path
import runpy
import duckdb

STARTER_DIR = Path(__file__).resolve().parent
DB_PATH = STARTER_DIR / "pulseiq.duckdb"

# Start from a clean database so the CREATE VIEW statements do not collide.
for path in (DB_PATH, DB_PATH.with_name(DB_PATH.name + ".wal")):
    path.unlink(missing_ok=True)

# Load all CSV files into the raw schema.
runpy.run_path(str(STARTER_DIR / "load_to_duckdb.py"))

con = duckdb.connect(str(DB_PATH))

# Governed metric layer (m01-m28) and average headcount (m31).
con.execute((STARTER_DIR / "metric_views.sql").read_text(encoding="utf-8"))
con.execute((STARTER_DIR / "create_m31.sql").read_text(encoding="utf-8"))

# The workforce views read from the warehouse schema, which is
# exposed as views over the raw tables.
con.execute("CREATE SCHEMA IF NOT EXISTS warehouse")
for table_name in ("dim_employee", "dim_location"):
    con.execute(
        f"""
        CREATE OR REPLACE VIEW warehouse."{table_name}" AS
        SELECT *
        FROM raw."{table_name}"
        """
    )

con.close()

# Workforce views (m29-m30).
runpy.run_path(str(STARTER_DIR / "create_workforce_views.py"))

print("\nDatabase build completed successfully.")
