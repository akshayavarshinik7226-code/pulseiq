from pathlib import Path
import runpy

import duckdb
import streamlit as st

# --------------------------------------------------
# PulseIQ | Deployment entry point
# --------------------------------------------------
# Runs the dashboard in pulseiq-task-PQ-01/05_Starter from the
# repository root, building the DuckDB database on first start.

STARTER_DIR = Path(__file__).resolve().parent / "pulseiq-task-PQ-01" / "05_Starter"
DB_PATH = STARTER_DIR / "pulseiq.duckdb"


def database_is_complete():
    if not DB_PATH.exists():
        return False
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        try:
            # m29-m31 are the last views created by build_db.py.
            con.execute("SELECT 1 FROM m29_location_tier LIMIT 1")
            con.execute("SELECT 1 FROM m31_average_headcount LIMIT 1")
        finally:
            con.close()
        return True
    except duckdb.Error:
        return False


@st.cache_resource(show_spinner="Preparing the PulseIQ database...")
def ensure_database():
    if not database_is_complete():
        runpy.run_path(str(STARTER_DIR / "build_db.py"))
    return True


ensure_database()

pages = [st.Page(str(STARTER_DIR / "app.py"), title="Workforce", default=True)]
pages += [
    st.Page(str(page), title=page.stem.split("_", 1)[1].replace("_", " "))
    for page in sorted((STARTER_DIR / "pages").glob("*.py"))
]

st.navigation(pages).run()
