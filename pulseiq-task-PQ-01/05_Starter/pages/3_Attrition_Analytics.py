from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="PulseIQ — Attrition Analytics",
    page_icon="📉",
    layout="wide",
)

st.title("Attrition Analytics")
st.caption(
    "Exits, attrition, tenure and voluntary exits, with a separate "
    "predicted-risk view. Individual employees are never shown."
)


# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "pulseiq.duckdb"


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


con = get_connection()


# ---------------------------------------------------------
# Load governed monthly attrition metrics
# ---------------------------------------------------------
monthly = con.execute(
    """
    SELECT
        month_start_date,
        department_id,
        exits,
        headcount_start,
        headcount_end,
        voluntary_exits,
        attrition_rate_monthly_pct AS attrition_rate_pct
    FROM raw.fact_headcount_monthly
    WHERE headcount_start >= 10
    ORDER BY month_start_date, department_id
    """
).fetchdf()

# Reconcile the displayed attrition percentage with the
# authoritative metric view.
governed_attrition = con.execute(
    """
    SELECT
        month_start_date,
        department_id,
        attrition_rate_pct
    FROM main.m04_attrition_rate_monthly
    ORDER BY month_start_date, department_id
    """
).fetchdf()

monthly = monthly.drop(columns=["attrition_rate_pct"]).merge(
    governed_attrition,
    on=["month_start_date", "department_id"],
    how="left",
)


# ---------------------------------------------------------
# Load employee exit records for tenure analysis
# ---------------------------------------------------------
exits = con.execute(
    """
    SELECT
        employee_id,
        department_id,
        hire_date,
        exit_date,
        employment_status
    FROM raw.dim_employee
    WHERE exit_date IS NOT NULL
      AND is_current = 'Y'
    """
).fetchdf()

exits["hire_date"] = pd.to_datetime(exits["hire_date"])
exits["exit_date"] = pd.to_datetime(exits["exit_date"])

exits["tenure_years"] = (
    (exits["exit_date"] - exits["hire_date"]).dt.days / 365.25
)

exits["tenure_band"] = pd.cut(
    exits["tenure_years"],
    bins=[-0.01, 1, 2, 3, 5, float("inf")],
    labels=[
        "<1 year",
        "1–2 years",
        "2–3 years",
        "3–5 years",
        "5+ years",
    ],
)


# ---------------------------------------------------------
# Latest predicted risk snapshot
# ---------------------------------------------------------
risk = con.execute(
    """
    SELECT
        as_of_date,
        department_id,
        risk_band,
        top_reason_1,
        top_reason_2,
        top_reason_3
    FROM raw.fact_attrition_risk
    """
).fetchdf()

latest_risk_date = risk["as_of_date"].max()

latest_risk = risk[
    risk["as_of_date"] == latest_risk_date
].copy()


# ---------------------------------------------------------
# Filters
# ---------------------------------------------------------
st.sidebar.header("Filters")

departments = sorted(monthly["department_id"].dropna().unique())

selected_departments = st.sidebar.multiselect(
    "Department",
    departments,
    default=departments,
)

min_month = monthly["month_start_date"].min().date()
max_month = monthly["month_start_date"].max().date()

selected_dates = st.sidebar.date_input(
    "Month range",
    value=(min_month, max_month),
    min_value=min_month,
    max_value=max_month,
)

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = min_month, max_month


filtered = monthly[
    monthly["department_id"].isin(selected_departments)
    & (monthly["month_start_date"].dt.date >= start_date)
    & (monthly["month_start_date"].dt.date <= end_date)
].copy()


filtered_exits = exits[
    exits["department_id"].isin(selected_departments)
    & (exits["exit_date"].dt.date >= start_date)
    & (exits["exit_date"].dt.date <= end_date)
].copy()


# ---------------------------------------------------------
# KPI calculations
# ---------------------------------------------------------
total_exits = int(filtered["exits"].sum())
voluntary_exits = int(filtered["voluntary_exits"].sum())

weighted_attrition = (
    filtered["exits"].sum() / filtered["headcount_start"].sum() * 100
    if filtered["headcount_start"].sum() > 0
    else 0
)

avg_tenure = (
    filtered_exits["tenure_years"].mean()
    if not filtered_exits.empty
    else 0
)


col1, col2, col3, col4 = st.columns(4)

col1.metric("Exits", f"{total_exits:,}")
col2.metric("Voluntary exits", f"{voluntary_exits:,}")
col3.metric("Attrition", f"{weighted_attrition:.2f}%")
col4.metric("Average tenure at exit", f"{avg_tenure:.2f} yrs")


# ---------------------------------------------------------
# Monthly attrition trend
# ---------------------------------------------------------
st.subheader("Monthly attrition")

monthly_summary = (
    filtered.groupby("month_start_date", as_index=False)
    .agg(
        exits=("exits", "sum"),
        voluntary_exits=("voluntary_exits", "sum"),
        headcount_start=("headcount_start", "sum"),
    )
)

monthly_summary["attrition_pct"] = (
    monthly_summary["exits"]
    / monthly_summary["headcount_start"].replace(0, pd.NA)
    * 100
)

fig = px.line(
    monthly_summary,
    x="month_start_date",
    y="attrition_pct",
    markers=True,
    labels={
        "month_start_date": "Month",
        "attrition_pct": "Attrition %",
    },
    title="Monthly attrition rate",
)

st.plotly_chart(fig, use_container_width=True)

if not monthly_summary.empty:
    peak = monthly_summary.loc[
        monthly_summary["attrition_pct"].idxmax()
    ]
    st.caption(
        f"Insight: attrition peaked at {peak['attrition_pct']:.2f}% "
        f"in {peak['month_start_date'].strftime('%b %Y')}."
    )


# ---------------------------------------------------------
# Department attrition
# ---------------------------------------------------------
st.subheader("Attrition by department")

dept_summary = (
    filtered.groupby("department_id", as_index=False)
    .agg(
        exits=("exits", "sum"),
        headcount_start=("headcount_start", "sum"),
        voluntary_exits=("voluntary_exits", "sum"),
    )
)

dept_summary["attrition_pct"] = (
    dept_summary["exits"]
    / dept_summary["headcount_start"].replace(0, pd.NA)
    * 100
)

dept_summary = dept_summary.sort_values(
    "attrition_pct",
    ascending=False,
)

fig = px.bar(
    dept_summary,
    x="department_id",
    y="attrition_pct",
    text="attrition_pct",
    labels={
        "department_id": "Department",
        "attrition_pct": "Attrition %",
    },
    title="Department attrition rate",
)

fig.update_traces(
    texttemplate="%{text:.2f}%",
    textposition="outside",
)

st.plotly_chart(fig, use_container_width=True)

if not dept_summary.empty:
    top_dept = dept_summary.iloc[0]
    st.caption(
        f"Insight: {top_dept['department_id']} has the highest "
        f"filtered attrition rate at {top_dept['attrition_pct']:.2f}%."
    )


# ---------------------------------------------------------
# Exit volume and voluntary exits
# ---------------------------------------------------------
st.subheader("Exit volume")

exit_chart = monthly_summary.melt(
    id_vars=["month_start_date"],
    value_vars=["exits", "voluntary_exits"],
    var_name="exit_type",
    value_name="count",
)

exit_chart["exit_type"] = exit_chart["exit_type"].replace(
    {
        "exits": "All exits",
        "voluntary_exits": "Voluntary exits",
    }
)

fig = px.bar(
    exit_chart,
    x="month_start_date",
    y="count",
    color="exit_type",
    barmode="group",
    labels={
        "month_start_date": "Month",
        "count": "Exit count",
        "exit_type": "Exit type",
    },
    title="Monthly exits and voluntary exits",
)

st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------
# Tenure at exit
# ---------------------------------------------------------
st.subheader("Tenure at exit")

tenure_summary = (
    filtered_exits.groupby("tenure_band", observed=False)
    .size()
    .reset_index(name="exits")
)

fig = px.bar(
    tenure_summary,
    x="tenure_band",
    y="exits",
    text="exits",
    labels={
        "tenure_band": "Tenure at exit",
        "exits": "Exits",
    },
    title="Exits by tenure at exit",
)

fig.update_traces(
    textposition="outside",
)

st.plotly_chart(fig, use_container_width=True)

if not filtered_exits.empty:
    most_common_band = tenure_summary.loc[
        tenure_summary["exits"].idxmax()
    ]

    st.caption(
        f"Insight: the largest exit group is "
        f"{most_common_band['tenure_band']} with "
        f"{int(most_common_band['exits'])} exits."
    )


# ---------------------------------------------------------
# Predicted risk section
# ---------------------------------------------------------
st.divider()

st.header("Predicted, not certain")
st.warning(
    "This section contains model predictions, not confirmed future exits. "
    "It should be used as an early-warning signal rather than a decision "
    "about any individual employee."
)

st.caption(
    f"Latest prediction snapshot: {latest_risk_date.strftime('%d %b %Y')}."
)

# Minimum group size rule: at least 10 predicted employees.
risk_dept = (
    latest_risk.groupby("department_id")
    .agg(
        predictions=("risk_band", "size"),
        high_risk=("risk_band", lambda s: (s == "High").sum()),
    )
    .reset_index()
)

risk_dept = risk_dept[
    risk_dept["predictions"] >= 10
].copy()

risk_dept["high_risk_share_pct"] = (
    risk_dept["high_risk"]
    / risk_dept["predictions"]
    * 100
)

risk_dept = risk_dept[
    risk_dept["department_id"].isin(selected_departments)
].sort_values(
    "high_risk_share_pct",
    ascending=False,
)

fig = px.bar(
    risk_dept,
    x="department_id",
    y="high_risk_share_pct",
    text="high_risk_share_pct",
    labels={
        "department_id": "Department",
        "high_risk_share_pct": "Predicted high-risk share",
    },
    title="Predicted high-risk share by department",
)

fig.update_traces(
    texttemplate="%{text:.1f}%",
    textposition="outside",
)

st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------
# Predicted risk bands
# ---------------------------------------------------------
risk_band_summary = (
    latest_risk[
        latest_risk["department_id"].isin(selected_departments)
    ]
    .groupby("risk_band")
    .size()
    .reset_index(name="predictions")
)

fig = px.bar(
    risk_band_summary,
    x="risk_band",
    y="predictions",
    text="predictions",
    labels={
        "risk_band": "Predicted risk band",
        "predictions": "Predicted employees",
    },
    title="Latest predicted risk bands",
)

fig.update_traces(
    textposition="outside",
)

st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------
# Aggregated prediction reasons
# ---------------------------------------------------------
st.subheader("Predicted risk reasons — aggregated")

reason_columns = [
    "top_reason_1",
    "top_reason_2",
    "top_reason_3",
]

reason_frames = []

for column in reason_columns:
    frame = latest_risk[
        latest_risk["department_id"].isin(selected_departments)
    ][["department_id", column]].rename(
        columns={column: "reason"}
    )
    reason_frames.append(frame)

reasons = pd.concat(reason_frames, ignore_index=True)

reasons = reasons.dropna()
reasons = reasons[reasons["reason"].astype(str).str.strip() != ""]

reason_summary = (
    reasons.groupby("reason")
    .size()
    .reset_index(name="mentions")
    .sort_values("mentions", ascending=False)
)

if reason_summary.empty:
    st.info("No prediction reasons are available for the selected groups.")
else:
    fig = px.bar(
        reason_summary.head(10),
        x="mentions",
        y="reason",
        orientation="h",
        labels={
            "mentions": "Reason mentions",
            "reason": "Predicted reason",
        },
        title="Most frequently cited predicted reasons",
    )

    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------
# Three biggest findings
# ---------------------------------------------------------
st.divider()

st.header("Three biggest findings")

findings = []

if not monthly_summary.empty:
    peak = monthly_summary.loc[
        monthly_summary["attrition_pct"].idxmax()
    ]
    findings.append(
        f"1. Peak monthly attrition was "
        f"{peak['attrition_pct']:.2f}% in "
        f"{peak['month_start_date'].strftime('%b %Y')}."
    )

if not dept_summary.empty:
    top_dept = dept_summary.iloc[0]
    findings.append(
        f"2. {top_dept['department_id']} had the highest filtered "
        f"department attrition rate at "
        f"{top_dept['attrition_pct']:.2f}%."
    )

if not filtered_exits.empty:
    avg_exit_tenure = filtered_exits["tenure_years"].mean()
    findings.append(
        f"3. Average tenure at exit was "
        f"{avg_exit_tenure:.2f} years across "
        f"{len(filtered_exits):,} exit records."
    )

for finding in findings:
    st.write(finding)


# ---------------------------------------------------------
# Data limitations
# ---------------------------------------------------------
st.divider()

with st.expander("Definitions and limitations"):
    st.markdown(
        """
        **Attrition %:** governed by `main.m04_attrition_rate_monthly`,
        using exits divided by starting headcount. The governed metric
        requires starting headcount of at least 10.

        **Exit counts:** sourced from `fact_headcount_monthly`.

        **Voluntary exits:** sourced from `voluntary_exits` in
        `fact_headcount_monthly`. The existing `m06_voluntary_attrition_rate`
        is a separate 12-month rolling metric and is not substituted for
        monthly voluntary-exit counts.

        **Tenure at exit:** calculated from `hire_date` to `exit_date`
        using current employee-dimension records.

        **Predicted risk:** sourced from `fact_attrition_risk` using the
        latest available prediction snapshot. Department risk is shown only
        when at least 10 predicted employees are present.

        **Privacy:** no employee names or employee IDs are displayed in
        risk views.

        **Exit reason limitation:** the supplied employee dimension does not
        contain a dedicated exit-reason field. `change_reason` is therefore
        not presented as an exit reason.

        **Prediction caution:** predicted risk is an early-warning signal,
        not a confirmed future outcome.
        """
    )