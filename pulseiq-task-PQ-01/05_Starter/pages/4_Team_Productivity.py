
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------
# PulseIQ | PQ-08 Team Productivity
# --------------------------------------------------

st.set_page_config(
    page_title="PulseIQ | Team Productivity",
    page_icon="📊",
    layout="wide",
)

st.title("Team Productivity Dashboard")
st.caption(
    "PQ-08 | Velocity, cycle time, delivery predictability, "
    "blocked work, and reopened tasks"
)

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "03_Data" / "csv"

TASK_FILE = DATA_DIR / "fact_task.csv"
TEAM_FILE = DATA_DIR / "dim_team.csv"
SPRINT_FILE = DATA_DIR / "dim_sprint.csv"


@st.cache_data
def load_data():
    tasks = pd.read_csv(TASK_FILE)
    teams = pd.read_csv(TEAM_FILE)
    sprints = pd.read_csv(SPRINT_FILE)

    for col in ["story_points", "reopened_count", "cycle_time_days"]:
        tasks[col] = pd.to_numeric(tasks[col], errors="coerce")

    for col in ["created_date", "started_date", "due_date", "completed_date"]:
        tasks[col] = pd.to_datetime(tasks[col], errors="coerce")

    for col in ["status", "completed_on_time", "is_overdue_at_cutoff"]:
        tasks[col] = tasks[col].astype("string").str.strip()

    tasks["completed_on_time"] = tasks["completed_on_time"].str.upper()
    tasks["is_overdue_at_cutoff"] = (
        tasks["is_overdue_at_cutoff"].str.upper()
    )

    teams["active_members"] = pd.to_numeric(
        teams["active_members"], errors="coerce"
    )
    sprints["working_days"] = pd.to_numeric(
        sprints["working_days"], errors="coerce"
    )

    return tasks, teams, sprints


try:
    tasks, teams, sprints = load_data()
except Exception as exc:
    st.error("Could not load the PQ-08 source files.")
    st.code(str(exc))
    st.stop()


# --------------------------------------------------
# Documented metric rules
# --------------------------------------------------

with st.expander("Metric definitions and data rules", expanded=False):
    st.markdown(
        """
        - **Velocity:** Sum of story points for tasks with status `Done`,
          grouped by team and sprint.
        - **Cycle time:** Average elapsed cycle time in days for `Done`
          tasks with a valid `cycle_time_days` value. The median is also
          available in the team summary.
        - **On-time rate:** Completed tasks marked `Y` divided by completed
          tasks explicitly marked `Y` or `N`.
        - **Overdue:** Tasks marked `is_overdue_at_cutoff = Y`. This is the
          source dataset's cutoff indicator, not a live calculation.
        - **Blocked:** Tasks whose current status is `Blocked`.
        - **Reopened:** Tasks with `reopened_count > 0`. Reopen events are
          reported separately as the sum of `reopened_count`.
        - **Cancelled:** Excluded from completed velocity, cycle time,
          and on-time delivery calculations. Cancelled tasks are shown
          separately, not treated as unfinished work.
        - **Fair comparisons:** Raw output depends on team size, task mix,
          sprint duration, and workload. Points per active member is shown
          as a simple size-normalized indicator, not a definitive
          productivity ranking.
        """
    )


# --------------------------------------------------
# Filters
# --------------------------------------------------

st.sidebar.header("Productivity filters")

sprint_options = sprints.sort_values("start_date")
sprint_labels = {
    row["sprint_id"]: (
        f'{row["sprint_name"]} '
        f'({row["start_date"]} to {row["end_date"]})'
    )
    for _, row in sprint_options.iterrows()
}

selected_sprint = st.sidebar.selectbox(
    "Sprint",
    options=["All sprints"] + sprint_options["sprint_id"].tolist(),
    format_func=lambda value: (
        "All sprints" if value == "All sprints"
        else sprint_labels.get(value, value)
    ),
)

team_options = teams.sort_values("team_name")
selected_teams = st.sidebar.multiselect(
    "Teams",
    options=team_options["team_id"].tolist(),
    default=team_options["team_id"].tolist(),
    format_func=lambda team_id: team_options.loc[
        team_options["team_id"] == team_id, "team_name"
    ].iloc[0],
)

filtered = tasks[tasks["team_id"].isin(selected_teams)].copy()

if selected_sprint != "All sprints":
    filtered = filtered[filtered["sprint_id"] == selected_sprint]

if filtered.empty:
    st.warning("No tasks match the selected filters.")
    st.stop()

eligible = filtered[filtered["status"] != "Cancelled"].copy()
done = eligible[eligible["status"] == "Done"].copy()

cancelled_count = int((filtered["status"] == "Cancelled").sum())
blocked_count = int((eligible["status"] == "Blocked").sum())
overdue_count = int(
    (eligible["is_overdue_at_cutoff"] == "Y").sum()
)
reopened_tasks_count = int(
    (eligible["reopened_count"] > 0).sum()
)
reopen_events = int(
    eligible["reopened_count"].fillna(0).sum()
)

known_delivery = done[
    done["completed_on_time"].isin(["Y", "N"])
]
on_time_count = int(
    (known_delivery["completed_on_time"] == "Y").sum()
)
on_time_rate = (
    100 * on_time_count / len(known_delivery)
    if len(known_delivery) else float("nan")
)

total_points = done["story_points"].sum(min_count=1)
average_cycle = done["cycle_time_days"].mean()

# --------------------------------------------------
# KPI cards
# --------------------------------------------------

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "Completed story points",
    f"{total_points:,.0f}" if pd.notna(total_points) else "N/A",
)
k2.metric(
    "Average cycle time",
    f"{average_cycle:.2f} days" if pd.notna(average_cycle) else "N/A",
)
k3.metric(
    "On-time delivery",
    f"{on_time_rate:.2f}%" if pd.notna(on_time_rate) else "N/A",
)
k4.metric("Blocked tasks", f"{blocked_count:,}")
k5.metric("Tasks reopened", f"{reopened_tasks_count:,}")

st.caption(
    f"Tasks in current filter: {len(filtered):,} | "
    f"Cancelled (excluded from delivery metrics): {cancelled_count:,} | "
    f"Reopen events: {reopen_events:,} | "
    f"Overdue at source cutoff: {overdue_count:,}"
)


# --------------------------------------------------
# Sprint velocity
# --------------------------------------------------

st.subheader("Velocity by team and sprint")

velocity = (
    done.groupby(["team_id", "sprint_id"], as_index=False)
    .agg(
        completed_story_points=("story_points", "sum"),
        completed_tasks=("task_id", "nunique"),
    )
    .merge(
        teams[["team_id", "team_name", "active_members"]],
        on="team_id",
        how="left",
    )
    .merge(
        sprints[["sprint_id", "sprint_name", "working_days"]],
        on="sprint_id",
        how="left",
    )
)

if not velocity.empty:
    if selected_sprint == "All sprints":
        velocity_chart = (
            velocity.groupby(
                ["team_id", "team_name", "active_members"],
                as_index=False,
            )
            .agg(
                completed_story_points=("completed_story_points", "sum"),
                completed_tasks=("completed_tasks", "sum"),
            )
        )
        velocity_chart["points_per_member"] = (
            velocity_chart["completed_story_points"]
            / velocity_chart["active_members"]
        )

        fig_velocity = px.bar(
            velocity_chart.sort_values(
                "completed_story_points", ascending=False
            ),
            x="team_name",
            y="completed_story_points",
            hover_data=[
                "completed_tasks",
                "active_members",
                "points_per_member",
            ],
            title="Completed story points across selected sprints",
            labels={
                "team_name": "Team",
                "completed_story_points": "Story points",
            },
        )
    else:
        fig_velocity = px.bar(
            velocity,
            x="team_name",
            y="completed_story_points",
            hover_data=["completed_tasks", "working_days"],
            title=f"Velocity — {sprint_labels[selected_sprint]}",
            labels={
                "team_name": "Team",
                "completed_story_points": "Story points",
            },
        )

    st.plotly_chart(fig_velocity, use_container_width=True)
else:
    st.info("No completed tasks with velocity data in this selection.")


# --------------------------------------------------
# Team health indicators
# --------------------------------------------------

st.subheader("Delivery quality and workflow health")

health = eligible.groupby("team_id", as_index=False).agg(
    non_cancelled_tasks=("task_id", "nunique"),
    blocked_tasks=("status", lambda s: int((s == "Blocked").sum())),
    overdue_tasks=("is_overdue_at_cutoff", lambda s: int((s == "Y").sum())),
    reopened_tasks=("reopened_count", lambda s: int((s > 0).sum())),
    reopen_events=("reopened_count", "sum"),
)

completed_metrics = done.groupby("team_id", as_index=False).agg(
    completed_tasks=("task_id", "nunique"),
    completed_story_points=("story_points", "sum"),
    average_cycle_days=("cycle_time_days", "mean"),
    median_cycle_days=("cycle_time_days", "median"),
)

delivery = (
    done[done["completed_on_time"].isin(["Y", "N"])]
    .groupby("team_id", as_index=False)
    .agg(
        delivery_denominator=("task_id", "nunique"),
        on_time_tasks=(
            "completed_on_time",
            lambda s: int((s == "Y").sum()),
        ),
    )
)

health = (
    teams[["team_id", "team_name", "active_members"]]
    .merge(health, on="team_id", how="left")
    .merge(completed_metrics, on="team_id", how="left")
    .merge(delivery, on="team_id", how="left")
)

health["on_time_rate_pct"] = (
    100 * health["on_time_tasks"] / health["delivery_denominator"]
)
health["points_per_member"] = (
    health["completed_story_points"] / health["active_members"]
)
health["blocked_rate_pct"] = (
    100 * health["blocked_tasks"] / health["non_cancelled_tasks"]
)
health["reopened_rate_pct"] = (
    100 * health["reopened_tasks"] / health["non_cancelled_tasks"]
)

health["average_cycle_days"] = health["average_cycle_days"].round(2)
health["median_cycle_days"] = health["median_cycle_days"].round(2)
health["on_time_rate_pct"] = health["on_time_rate_pct"].round(2)
health["points_per_member"] = health["points_per_member"].round(2)
health["blocked_rate_pct"] = health["blocked_rate_pct"].round(2)
health["reopened_rate_pct"] = health["reopened_rate_pct"].round(2)

health = health[health["team_id"].isin(selected_teams)].copy()

left, right = st.columns(2)

with left:
    fig_cycle = px.bar(
        health.sort_values("average_cycle_days", ascending=False),
        x="team_name",
        y="average_cycle_days",
        hover_data=["median_cycle_days", "completed_tasks"],
        title="Average cycle time by team",
        labels={
            "team_name": "Team",
            "average_cycle_days": "Average days",
        },
    )
    st.plotly_chart(fig_cycle, use_container_width=True)

with right:
    fig_delivery = px.bar(
        health.sort_values("on_time_rate_pct", ascending=False),
        x="team_name",
        y="on_time_rate_pct",
        hover_data=["on_time_tasks", "delivery_denominator"],
        title="On-time delivery rate by team",
        labels={
            "team_name": "Team",
            "on_time_rate_pct": "On-time rate (%)",
        },
    )
    st.plotly_chart(fig_delivery, use_container_width=True)

left, right = st.columns(2)

with left:
    fig_blocked = px.bar(
        health.sort_values("blocked_rate_pct", ascending=False),
        x="team_name",
        y="blocked_rate_pct",
        hover_data=["blocked_tasks", "non_cancelled_tasks"],
        title="Blocked-task rate by team",
        labels={
            "team_name": "Team",
            "blocked_rate_pct": "Blocked tasks (%)",
        },
    )
    st.plotly_chart(fig_blocked, use_container_width=True)

with right:
    fig_reopened = px.bar(
        health.sort_values("reopened_rate_pct", ascending=False),
        x="team_name",
        y="reopened_rate_pct",
        hover_data=["reopened_tasks", "reopen_events"],
        title="Reopened-task rate by team",
        labels={
            "team_name": "Team",
            "reopened_rate_pct": "Tasks reopened (%)",
        },
    )
    st.plotly_chart(fig_reopened, use_container_width=True)


# --------------------------------------------------
# Detailed verification table
# --------------------------------------------------

st.subheader("Team metrics detail")

display_cols = [
    "team_id",
    "team_name",
    "active_members",
    "completed_tasks",
    "completed_story_points",
    "points_per_member",
    "average_cycle_days",
    "median_cycle_days",
    "on_time_tasks",
    "delivery_denominator",
    "on_time_rate_pct",
    "blocked_tasks",
    "blocked_rate_pct",
    "overdue_tasks",
    "reopened_tasks",
    "reopen_events",
    "reopened_rate_pct",
]

st.dataframe(
    health[display_cols]
    .sort_values("team_name")
    .reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
)

csv_data = health[display_cols].to_csv(index=False).encode("utf-8")
st.download_button(
    "Download team metrics CSV",
    data=csv_data,
    file_name="pq08_team_metrics.csv",
    mime="text/csv",
)


# --------------------------------------------------
# Evidence-based findings
# --------------------------------------------------

st.subheader("Team health findings")

if not health.empty:
    high_velocity = health.loc[
        health["completed_story_points"].idxmax()
    ]
    best_on_time = health.loc[
        health["on_time_rate_pct"].idxmax()
    ]
    longest_cycle = health.loc[
        health["average_cycle_days"].idxmax()
    ]

    st.markdown(
        f"""
        1. **Highest total velocity:** {high_velocity['team_name']} recorded
           {high_velocity['completed_story_points']:,.0f} completed story
           points. Consider its team size
           ({high_velocity['active_members']:.0f} active members) and task
           mix before comparing it directly with smaller teams.

        2. **Strongest on-time delivery:** {best_on_time['team_name']} achieved
           {best_on_time['on_time_rate_pct']:.2f}% on-time delivery among
           {best_on_time['delivery_denominator']:,.0f} completed tasks with
           a known on-time indicator. Its cycle time and reopened-work rate
           should also be reviewed before concluding overall health.

        3. **Longest average cycle time:** {longest_cycle['team_name']} averaged
           {longest_cycle['average_cycle_days']:.2f} days per completed task.
           Investigate task type, priority, blocked work, and sprint context
           before attributing the result to team performance.
        """
    )

st.caption(
    "Source: fictional PulseIQ training dataset. "
    "Metrics are descriptive and do not establish causation."
)

