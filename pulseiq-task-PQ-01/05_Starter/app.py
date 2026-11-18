from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------
# PulseIQ | Workforce & Headcount Dashboard
# --------------------------------------------------

st.set_page_config(
    page_title="PulseIQ | Workforce",
    page_icon="📊",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parent / "pulseiq.duckdb"

st.title("PulseIQ | Workforce Intelligence")
st.caption("Workforce & Headcount | Executive Dashboard")

# Keep the dashboard visually consistent with three main colours.
NAVY = "#17324D"
TEAL = "#168C8C"
GOLD = "#E6A23C"

if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
    st.stop()


@st.cache_data(ttl=300)
def load_workforce_data():
    """Read governed metrics and return aggregated dashboard data."""

    con = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        # Headcount trend: governed metric view only.
        headcount = con.execute("""
            SELECT
                month_start_date,
                department_id,
                SUM(headcount) AS headcount
            FROM m01_headcount
            GROUP BY month_start_date, department_id
            ORDER BY month_start_date, department_id
        """).fetchdf()

        # Hiring and exits: governed metric views only.
        hires = con.execute("""
            SELECT month_start_date, department_id, SUM(hires) AS hires
            FROM m02_hires
            GROUP BY month_start_date, department_id
        """).fetchdf()

        exits = con.execute("""
            SELECT month_start_date, department_id, SUM(exits) AS exits
            FROM m03_exits
            GROUP BY month_start_date, department_id
        """).fetchdf()

        # Aggregate employee attributes into a governed view-shaped query.
        # This query will be replaced by governed views in the next step.
        # The app itself must not query raw or dimension tables.
        department = con.execute("""
            SELECT department_id, SUM(headcount) AS employees
            FROM m01_headcount
            WHERE month_start_date = (
                SELECT MAX(month_start_date) FROM m01_headcount
            )
            GROUP BY department_id
            ORDER BY employees DESC
        """).fetchdf()

        # These are governed summary views created for the dashboard.
        location_tier = con.execute("""
            SELECT tier_name, employees
            FROM m29_location_tier
            ORDER BY tier_name
        """).fetchdf()

        work_mode = con.execute("""
            SELECT work_mode, employees
            FROM m30_work_mode
            ORDER BY employees DESC
        """).fetchdf()
        average_headcount = con.execute("""
            SELECT average_headcount
            FROM m31_average_headcount
        """).fetchone()[0]

        return (
    headcount,
    hires,
    exits,
    department,
    location_tier,
    work_mode,
    average_headcount,
)

    finally:
        con.close()


try:
    headcount, hires, exits, department, location_tier, work_mode, average_headcount = (
    load_workforce_data()
    )
except Exception as exc:
    st.error("The dashboard's supporting metric views are not ready yet.")
    st.code(str(exc))
    st.info(
        "We'll create and validate the missing governed summary views "
        "before running the dashboard."
    )
    st.stop()


# --------------------------------------------------
# Filters
# --------------------------------------------------

headcount["month_start_date"] = pd.to_datetime(
    headcount["month_start_date"]
)

min_date = headcount["month_start_date"].min().date()
max_date = headcount["month_start_date"].max().date()

st.sidebar.header("Dashboard Filters")

departments = sorted(headcount["department_id"].dropna().unique().tolist())

selected_departments = st.sidebar.multiselect(
    "Department",
    departments,
    default=departments,
)

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered = headcount[
    headcount["department_id"].isin(selected_departments)
    & headcount["month_start_date"].dt.date.between(start_date, end_date)
]

if filtered.empty:
    st.warning("No workforce data matches these filters.")
    st.stop()

latest_month = filtered["month_start_date"].max()

latest_headcount = int(
    filtered.loc[
        filtered["month_start_date"] == latest_month, "headcount"
    ].sum()
)

previous_months = filtered[
    filtered["month_start_date"] < latest_month
]["month_start_date"].unique()

previous_headcount = None

if len(previous_months):
    previous_month = max(previous_months)
    previous_headcount = int(
        filtered.loc[
            filtered["month_start_date"] == previous_month, "headcount"
        ].sum()
    )

latest_hires = hires[
    hires["month_start_date"].between(
        pd.Timestamp(start_date), pd.Timestamp(end_date)
    )
    & hires["department_id"].isin(selected_departments)
]["hires"].sum()

latest_exits = exits[
    exits["month_start_date"].between(
        pd.Timestamp(start_date), pd.Timestamp(end_date)
    )
    & exits["department_id"].isin(selected_departments)
]["exits"].sum()


# --------------------------------------------------
# KPI Cards
# --------------------------------------------------

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Headcount",
    f"{latest_headcount:,}",
    (
        f"{latest_headcount - previous_headcount:+,} vs previous month"
        if previous_headcount is not None
        else None
    ),
)

k2.metric("Hires in selected period", f"{int(latest_hires):,}")
k3.metric("Exits in selected period", f"{int(latest_exits):,}")
k4.metric("Average Headcount", f"{average_headcount:,.2f}")

st.caption(
    f"Headcount is shown for {latest_month:%B %Y}. "
    "Hires and exits cover the selected date range."
)

st.divider()


# --------------------------------------------------
# Chart 1: Headcount Trend
# --------------------------------------------------

trend = (
    filtered.groupby("month_start_date", as_index=False)["headcount"]
    .sum()
    .sort_values("month_start_date")
)

if len(trend) >= 2:
    first_value = int(trend.iloc[0]["headcount"])
    last_value = int(trend.iloc[-1]["headcount"])
    change = last_value - first_value

    trend_title = (
        f"Headcount {'increased' if change >= 0 else 'decreased'} "
        f"by {abs(change):,} across the selected period"
    )
else:
    trend_title = "Headcount for the selected period"

st.subheader(trend_title)

fig_trend = px.line(
    trend,
    x="month_start_date",
    y="headcount",
    markers=True,
    labels={
        "month_start_date": "Month",
        "headcount": "Employees",
    },
)

fig_trend.update_traces(line=dict(color=TEAL, width=3))
fig_trend.update_layout(margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig_trend, use_container_width=True)

if len(trend) >= 2:
    st.caption(
        f"Insight: Headcount moved from {first_value:,} to "
        f"{last_value:,}, a net change of {change:+,}."
    )
else:
    st.caption(f"Insight: {latest_headcount:,} employees are represented.")


# --------------------------------------------------
# Chart 2: Department Breakdown
# --------------------------------------------------

st.subheader("Department workforce distribution")

department_filtered = department[
    department["department_id"].isin(selected_departments)
]

fig_department = px.bar(
    department_filtered.sort_values("employees", ascending=False),
    x="department_id",
    y="employees",
    labels={
        "department_id": "Department",
        "employees": "Employees",
    },
)

fig_department.update_traces(marker_color=NAVY)
fig_department.update_layout(margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig_department, use_container_width=True)

if not department_filtered.empty:
    top_department = department_filtered.loc[
        department_filtered["employees"].idxmax()
    ]
    st.caption(
        f"Insight: {top_department['department_id']} has the largest "
        f"department headcount at {int(top_department['employees']):,}."
    )


# --------------------------------------------------
# Chart 3: Location Tier
# --------------------------------------------------

st.subheader("Workforce distribution by location tier")

fig_location = px.bar(
    location_tier,
    x="tier_name",
    y="employees",
    labels={
        "tier_name": "Location tier",
        "employees": "Employees",
    },
)

fig_location.update_traces(marker_color=GOLD)
fig_location.update_layout(margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig_location, use_container_width=True)

if not location_tier.empty:
    largest_tier = location_tier.loc[
        location_tier["employees"].idxmax()
    ]
    st.caption(
        f"Insight: {largest_tier['tier_name']} has the most employees, "
        f"with {int(largest_tier['employees']):,}."
    )


# --------------------------------------------------
# Chart 4: Work Mode
# --------------------------------------------------

st.subheader("Workforce distribution by work mode")

fig_mode = px.bar(
    work_mode,
    x="work_mode",
    y="employees",
    labels={
        "work_mode": "Work mode",
        "employees": "Employees",
    },
)

fig_mode.update_traces(marker_color=TEAL)
fig_mode.update_layout(margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig_mode, use_container_width=True)

if not work_mode.empty:
    largest_mode = work_mode.loc[work_mode["employees"].idxmax()]
    st.caption(
        f"Insight: {largest_mode['work_mode']} is the largest work mode, "
        f"with {int(largest_mode['employees']):,} employees."
    )

st.divider()
st.caption("PulseIQ | Governed metrics | Workforce Analytics")