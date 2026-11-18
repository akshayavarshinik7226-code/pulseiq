from pathlib import Path
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "03_Data" / "csv"
DB_PATH = Path(__file__).resolve().parent / "pulseiq.duckdb"

con = duckdb.connect(str(DB_PATH))
con.execute("CREATE SCHEMA IF NOT EXISTS raw")

csv_files = sorted(CSV_DIR.glob("*.csv"))

print(f"Found {len(csv_files)} CSV files.")

for csv_file in csv_files:
    table_name = csv_file.stem

    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw."{table_name}" AS
        SELECT *
        FROM read_csv_auto(?)
        """,
        [str(csv_file)]
    )

    row_count = con.execute(
        f'SELECT COUNT(*) FROM raw."{table_name}"'
    ).fetchone()[0]

    print(f"{table_name:35} {row_count:8} rows")

con.close()

print("\nCSV load completed successfully.")
