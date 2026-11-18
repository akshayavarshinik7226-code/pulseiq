from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="PulseIQ | Attendance & Leave",
    page_icon="📊",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parent.parent / "pulseiq.duckdb"

NAVY = "#17324D"
TEAL = "#168C8C"
GOLD = "#E6A23C"


@st.cache_data(ttl=300)
def load_data():
    """Load attendance, approved leave, calendar, and governed metrics."""
    con = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        attendance = con.execute("""
            SELECT
                period_end_date,
                department_id,
                COUNT(DISTINCT employee_id) AS employees,
                SUM(scheduled_days) AS scheduled_days,
                SUM(present_days) AS present_days,
                SUM(half_days_unpaid) AS half_days_unpaid,
                SUM(late_arrivals) AS late_arrivals,
                SUM(overtime_hours) AS overtime_hours,
                SUM(wfh_days) AS wfh_days,
                SUM(unpaid_absence_days) AS unpaid_absence_days
            FROM raw.fact_attendance_monthly
            GROUP BY period_end_date, department_id
            HAVING COUNT(DISTINCT employee_id) >= 5
            ORDER BY period_end_date, department_id
        """).fetchdf()

        overtime_share = con.execute("""
            SELECT period_end_date, department_id, overtime_share_pct
            FROM m11_overtime_share
        """).fetchdf()

        leave = con.execute("""
            SELECT
                start_date,
                end_date,
                leave_type_code,
                status,
                days,
                employee_id
            FROM raw.fact_leave
            WHERE status = 'Approved'
        """).fetchdf()

        calendar = con.execute("""
            SELECT
                date,
                day_of_week,
                is_weekend,
                is_holiday,
                is_working_day,
                month_start_date,
                month_end_date
            FROM raw.dim_date
        """).fetchdf()

        return attendance, overtime_share, leave, calendar

    finally:
        con.close()


if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
    st.stop()

try:
    attendance, overtime_share, leave, calendar = load_data()
except Exception as exc:
    st.error("Could not load the attendance and leave data.")
    st.exception(exc)
    st.stop()

if attendance.empty:
    st.warning("No attendance records are available.")
    st.stop()

for frame, columns in [
    (attendance, ["period_end_date"]),
    (overtime_share, ["period_end_date"]),
    (leave, ["start_date", "end_date"]),
    (calendar, ["date", "month_start_date", "month_end_date"]),
]:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")

attendance["month"] = attendance["period_end_date"].dt.to_period("M").dt.to_timestamp()
attendance["attendance_rate"] = (
    attendance["present_days"] + 0.5 * attendance["half_days_unpaid"]
) / attendance["scheduled_days"].replace(0, pd.NA)
attendance["late_arrival_rate"] = (
    attendance["late_arrivals"] / attendance["present_days"].replace(0, pd.NA)
) * 100

attendance["attendance_pct"] = attendance["attendance_rate"] * 100

overtime_share["month"] = (
    overtime_share["period_end_date"].dt.to_period("M").dt.to_timestamp()
)

calendar["month"] = calendar["month_start_date"]

st.title("PulseIQ | Attendance & Leave")
st.caption(
    "Monthly attendance, punctuality, overtime, approved leave, "
    "and calendar patterns."
)

# --------------------------------------------------
# Filters
# --------------------------------------------------

st.sidebar.header("Attendance & Leave Filters")

departments = sorted(attendance["department_id"].dropna().unique().tolist())

selected_departments = st.sidebar.multiselect(
    "Department",
    options=departments,
    default=departments,
)

min_month = attendance["month"].min().date()
max_month = attendance["month"].max().date()

date_range = st.sidebar.date_input(
    "Month range",
    value=(min_month, max_month),
    min_value=min_month,
    max_value=max_month,
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_month, max_month

start_month = pd.Timestamp(start_date).to_period("M").to_timestamp()
end_month = pd.Timestamp(end_date).to_period("M").to_timestamp()

selected = attendance[
    attendance["department_id"].isin(selected_departments)
    & attendance["month"].between(start_month, end_month)
].copy()

if selected.empty:
    st.warning("No attendance records match the selected filters.")
    st.stop()

# Use weighted ratios rather than averaging department percentages.
scheduled_total = selected["scheduled_days"].sum()
present_total = selected["present_days"].sum()
half_days_total = selected["half_days_unpaid"].sum()
late_total = selected["late_arrivals"].sum()
overtime_total = selected["overtime_hours"].sum()

overall_attendance = (
    (present_total + 0.5 * half_days_total) / scheduled_total * 100
    if scheduled_total else 0
)
overall_late_rate = (
    late_total / present_total * 100 if present_total else 0
)

leave_selected = leave[
    leave["start_date"].notna()
    & leave["start_date"].dt.to_period("M").dt.to_timestamp().between(
        start_month, end_month
    )
].copy()

# Leave requests do not contain department_id. Resolve each employee's
# department from the attendance data for the matching month where possible.
employee_department = duckdb.connect(str(DB_PATH), read_only=True)
try:
    leave_department = employee_department.execute("""
        SELECT employee_id, department_id, period_end_date
        FROM raw.fact_attendance_monthly
    """).fetchdf()
finally:
    employee_department.close()

leave_department["period_end_date"] = pd.to_datetime(
    leave_department["period_end_date"]
)
leave_department["month"] = (
    leave_department["period_end_date"].dt.to_period("M").dt.to_timestamp()
)

leave_selected["month"] = (
    leave_selected["start_date"].dt.to_period("M").dt.to_timestamp()
)

leave_selected = leave_selected.merge(
    leave_department[["employee_id", "department_id", "month"]].drop_duplicates(),
    on=["employee_id", "month"],
    how="left",
)

if selected_departments:
    leave_selected = leave_selected[
        leave_selected["department_id"].isin(selected_departments)
    ]
else:
    leave_selected = leave_selected.iloc[0:0]

approved_leave_days = leave_selected["days"].sum()

# --------------------------------------------------
# KPI cards
# --------------------------------------------------

k1, k2, k3, k4 = st.columns(4)

k1.metric("Attendance rate", f"{overall_attendance:.2f}%")
k2.metric("Late arrivals / present days", f"{overall_late_rate:.2f}%")
k3.metric("Overtime hours", f"{overtime_total:,.0f}")
k4.metric("Approved leave days", f"{approved_leave_days:,.0f}")

st.caption(
    "Attendance = (present days + 0.5 × unpaid half-days) ÷ scheduled days. "
    "Late-arrival rate = late arrivals ÷ present days. "
    "Leave is assigned to the request's start month."
)

st.divider()

# --------------------------------------------------
# Monthly attendance and punctuality
# --------------------------------------------------

monthly = (
    selected.groupby("month", as_index=False)
    .agg(
        scheduled_days=("scheduled_days", "sum"),
        present_days=("present_days", "sum"),
        half_days_unpaid=("half_days_unpaid", "sum"),
        late_arrivals=("late_arrivals", "sum"),
        overtime_hours=("overtime_hours", "sum"),
        employees=("employees", "sum"),
    )
    .sort_values("month")
)

monthly["attendance_pct"] = (
    (monthly["present_days"] + 0.5 * monthly["half_days_unpaid"])
    / monthly["scheduled_days"].replace(0, pd.NA)
) * 100

monthly["late_arrival_rate"] = (
    monthly["late_arrivals"]
    / monthly["present_days"].replace(0, pd.NA)
) * 100

left, right = st.columns(2)

with left:
    st.subheader("Monthly attendance rate")

    fig_attendance = px.line(
        monthly,
        x="month",
        y="attendance_pct",
        markers=True,
        labels={"month": "Month", "attendance_pct": "Attendance (%)"},
    )
    fig_attendance.update_traces(line=dict(color=TEAL, width=3))
    fig_attendance.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_attendance, use_container_width=True)

with right:
    st.subheader("Late-arrival rate")

    fig_late = px.line(
        monthly,
        x="month",
        y="late_arrival_rate",
        markers=True,
        labels={"month": "Month", "late_arrival_rate": "Late arrivals / present days (%)"},
    )
    fig_late.update_traces(line=dict(color=GOLD, width=3))
    fig_late.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_late, use_container_width=True)

# --------------------------------------------------
# Overtime
# --------------------------------------------------

st.subheader("Monthly overtime hours")

fig_overtime = px.bar(
    monthly,
    x="month",
    y="overtime_hours",
    labels={"month": "Month", "overtime_hours": "Overtime hours"},
)
fig_overtime.update_traces(marker_color=NAVY)
fig_overtime.update_layout(margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig_overtime, use_container_width=True)

# --------------------------------------------------
# Approved leave trends
# --------------------------------------------------

st.subheader("Approved leave patterns")

if leave_selected.empty:
    st.info(
        "No approved leave requests could be matched to the selected "
        "departments and months."
    )
else:
    leave_monthly = (
        leave_selected.groupby(["month", "leave_type_code"], as_index=False)
        .agg(leave_days=("days", "sum"), requests=("employee_id", "size"))
        .sort_values("month")
    )

    fig_leave = px.bar(
        leave_monthly,
        x="month",
        y="leave_days",
        color="leave_type_code",
        barmode="stack",
        labels={
            "month": "Leave start month",
            "leave_days": "Approved leave days",
            "leave_type_code": "Leave type",
        },
    )
    fig_leave.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_leave, use_container_width=True)

# --------------------------------------------------
# Calendar: holidays and long weekends
# --------------------------------------------------

st.subheader("Holiday and long-weekend calendar")

calendar_period = calendar[
    calendar["date"].dt.to_period("M").dt.to_timestamp().between(
        start_month, end_month
    )
].copy()

if not calendar_period.empty:
    calendar_period["holiday_flag"] = calendar_period["is_holiday"].eq("Y")
    calendar_period["weekend_flag"] = calendar_period["is_weekend"].eq("Y")
    calendar_period["working_day_flag"] = calendar_period["is_working_day"].eq("Y")

    # A holiday adjacent to a weekend is marked as a potential long weekend.
    calendar_period["previous_date"] = calendar_period["date"] - pd.Timedelta(days=1)
    calendar_period["next_date"] = calendar_period["date"] + pd.Timedelta(days=1)

    weekend_dates = set(
        calendar_period.loc[calendar_period["weekend_flag"], "date"].dt.date
    )
    calendar_period["long_weekend_marker"] = calendar_period.apply(
        lambda row: (
            row["holiday_flag"]
            and (
                row["previous_date"].date() in weekend_dates
                or row["next_date"].date() in weekend_dates
            )
        ),
        axis=1,
    )

    calendar_period["calendar_marker"] = "Working day"
    calendar_period.loc[calendar_period["weekend_flag"], "calendar_marker"] = "Weekend"
    calendar_period.loc[calendar_period["holiday_flag"], "calendar_marker"] = "Holiday"
    calendar_period.loc[
        calendar_period["long_weekend_marker"], "calendar_marker"
    ] = "Holiday near weekend"

    fig_calendar = px.scatter(
        calendar_period,
        x="date",
        y="calendar_marker",
        color="calendar_marker",
        hover_data=["day_of_week", "is_weekend", "is_holiday", "is_working_day"],
        labels={"date": "Date", "calendar_marker": "Calendar marker"},
    )
    fig_calendar.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_calendar, use_container_width=True)

    holiday_table = calendar_period[
        calendar_period["holiday_flag"] | calendar_period["long_weekend_marker"]
    ][["date", "day_of_week", "is_weekend", "is_holiday", "is_working_day", "calendar_marker"]]

    if not holiday_table.empty:
        st.dataframe(holiday_table, use_container_width=True, hide_index=True)
else:
    st.info("No calendar dates are available for this period.")

# --------------------------------------------------
# Three unusual months
# --------------------------------------------------

st.subheader("Three unusual months")

insight_monthly = monthly.dropna(subset=["attendance_pct"]).copy()

if len(insight_monthly) >= 3:
    median_attendance = insight_monthly["attendance_pct"].median()
    insight_monthly["distance_from_median"] = (
        insight_monthly["attendance_pct"] - median_attendance
    ).abs()

    unusual = insight_monthly.nlargest(3, "distance_from_median").sort_values(
        "distance_from_median", ascending=False
    )

    for _, row in unusual.iterrows():
        direction = "above" if row["attendance_pct"] >= median_attendance else "below"
        st.write(
            f"- **{row['month']:%B %Y}:** attendance was "
            f"{row['attendance_pct']:.2f}%, "
            f"{abs(row['attendance_pct'] - median_attendance):.2f} percentage points "
            f"{direction} the selected-period median of {median_attendance:.2f}%. "
            f"Late arrivals: {int(row['late_arrivals']):,}; "
            f"overtime: {row['overtime_hours']:,.0f} hours."
        )
else:
    st.info("Select a range containing at least three months to identify unusual months.")

# --------------------------------------------------
# Optional weekday-by-month attendance heatmap
# --------------------------------------------------

st.subheader("Working days, weekends, and holidays by month")

calendar_counts = (
    calendar_period.groupby(["month", "is_working_day"], as_index=False)
    .size()
    .rename(columns={"size": "days"})
)

if not calendar_counts.empty:
    fig_calendar_counts = px.bar(
        calendar_counts,
        x="month",
        y="days",
        color="is_working_day",
        barmode="stack",
        labels={
            "month": "Month",
            "days": "Calendar days",
            "is_working_day": "Working-day flag",
        },
    )
    st.plotly_chart(fig_calendar_counts, use_container_width=True)

st.divider()
st.caption(
    "PulseIQ | Attendance & Leave Analytics | "
    "Leave is based on approved requests; long-weekend markers indicate "
    "holidays adjacent to a weekend."
)