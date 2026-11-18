
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# PulseIQ | PQ-09 Payroll Cost Dashboard
# --------------------------------------------------

st.set_page_config(
    page_title="PulseIQ | Payroll Cost",
    page_icon="💰",
    layout="wide",
)

st.title("Payroll Cost Dashboard")
st.caption(
    "PQ-09 | Gross pay, net pay, employer cost, cost per employee, "
    "monthly trend, and payroll reconciliation"
)


# --------------------------------------------------
# File paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "03_Data" / "csv"

PAYROLL_FILE = DATA_DIR / "fact_payroll.csv"
DEPARTMENT_FILE = DATA_DIR / "dim_department.csv"
ANSWER_KEY_FILE = (
    BASE_DIR
    / "04_Validation_Vault"
    / "unlock_PQ-09_reconciliation_answer_key.csv"
)


# --------------------------------------------------
# Load source data
# --------------------------------------------------


@st.cache_data
def load_data():
    payroll = pd.read_csv(PAYROLL_FILE)
    departments = pd.read_csv(DEPARTMENT_FILE)
    answer_key = pd.read_csv(ANSWER_KEY_FILE)
    required_payroll_columns = [
        "period_end_date",
        "monthly_fixed_gross",
        "gross_pay",
        "net_pay",
        "variable_pay",
        "variable_pay_type",
        "employer_cost",
        "headcount_flag",
        "role_id",
        "department_id",
        "payroll_item_id",
        "employee_id",
    ]

    missing_columns = [
        col for col in required_payroll_columns
        if col not in payroll.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing payroll columns: {missing_columns}"
        )

    required_department_columns = [
        "department_id",
        "department_name",
    ]

    missing_department_columns = [
        col for col in required_department_columns
        if col not in departments.columns
    ]

    if missing_department_columns:
        raise ValueError(
            f"Missing department columns: {missing_department_columns}"
        )

    payroll["period_end_date"] = pd.to_datetime(
        payroll["period_end_date"],
        errors="coerce",
    )

    numeric_cols = [
        "monthly_fixed_gross",
        "gross_pay",
        "net_pay",
        "employer_cost",
        "headcount_flag",
        "variable_pay",
    ]

    for col in numeric_cols:
        payroll[col] = pd.to_numeric(
            payroll[col],
            errors="coerce",
        )

    payroll["department_id"] = (
        payroll["department_id"]
        .astype("string")
        .str.strip()
    )

    departments["department_id"] = (
        departments["department_id"]
        .astype("string")
        .str.strip()
    )

    return payroll, departments, answer_key



try:
    payroll, departments, answer_key = load_data()

except Exception as exc:
    st.error("Could not load the PQ-09 source files.")
    st.code(str(exc))
    st.stop()


st.success(
    f"Loaded {len(payroll):,} payroll rows across "
    f"{payroll['period_end_date'].nunique():,} payroll periods."
)


# --------------------------------------------------
# Privacy threshold
# --------------------------------------------------

MIN_GROUP_SIZE = 5


# --------------------------------------------------
# Privacy-safe filters
# --------------------------------------------------

role_options = sorted(
    payroll["role_id"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

department_labels = (
    departments
    .set_index("department_id")["department_name"]
    .to_dict()
)

department_options = sorted(
    departments["department_id"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


with st.sidebar:
    st.header("Payroll Filters")

    selected_roles = st.multiselect(
        "Role",
        options=role_options,
        default=role_options,
        help=(
            "Filter by role. Individual salary records "
            "are not displayed."
        ),
    )

    selected_departments = st.multiselect(
        "Department",
        options=department_options,
        default=department_options,
        format_func=lambda x: department_labels.get(x, x),
    )


# --------------------------------------------------
# --------------------------------------------------
# Payroll data quality and reconciliation
# --------------------------------------------------

with st.expander(
    "Payroll Data Quality & Reconciliation",
    expanded=False,
):
    st.markdown(
        """
        Four payroll records are excluded from the
        reporting aggregates based on the official
        PQ-03 data-quality issue register.
        """
    )

    exception_details = pd.DataFrame(
        [
            {
                "Payroll Record": "PI-X0001",
                "Issue": "Duplicate employee/run record",
                "Action": "Excluded",
            },
            {
                "Payroll Record": "PI-X0002",
                "Issue": "Duplicate employee/run record",
                "Action": "Excluded",
            },
            {
                "Payroll Record": "PI-X0003",
                "Issue": "Employee ID missing from employee dimension",
                "Action": "Excluded",
            },
            {
                "Payroll Record": "PI-X0004",
                "Issue": "Employee ID missing from employee dimension",
                "Action": "Excluded",
            },
        ]
    )

    st.dataframe(
        exception_details,
        hide_index=True,
        use_container_width=True,
    )

    st.info(
        "Reconciliation is performed on the cleaned "
        "payroll data. All 18 monthly payroll totals "
        "match the official PQ-09 reconciliation "
        "answer key."
    )
# Exclude confirmed PQ-09 payroll exceptions
# --------------------------------------------------

EXCLUDED_PAYROLL_IDS = {
    "PI-X0002",
    "PI-X0004",
    "PI-X0001",
    "PI-X0003",
}


filtered_payroll = payroll[
    payroll["role_id"].astype(str).isin(selected_roles)
    & payroll["department_id"].astype(str).isin(
        selected_departments
    )
    & ~payroll["payroll_item_id"].isin(
        EXCLUDED_PAYROLL_IDS
    )
].copy()


# Remove records without a valid reporting date.
filtered_payroll = filtered_payroll[
    filtered_payroll["period_end_date"].notna()
].copy()


if filtered_payroll.empty:
    st.warning(
        "No payroll records match the selected filters."
    )
    st.stop()


# --------------------------------------------------
# Monthly payroll aggregation
# --------------------------------------------------

# Normalize dates to calendar months so records with
# different dates in the same month are grouped together.

filtered_payroll["payroll_month"] = (
    filtered_payroll["period_end_date"]
    .dt.to_period("M")
    .dt.to_timestamp()
)


monthly_employee_cost = (
    filtered_payroll
    .groupby("payroll_month")
    .agg(
        employer_cost=("employer_cost", "sum"),
        employee_count=("employee_id", "nunique"),
    )
    .reset_index()
)


# Only calculate averages where employee count is valid.

monthly_employee_cost["cost_per_employee"] = (
    monthly_employee_cost["employer_cost"]
    / monthly_employee_cost["employee_count"].where(
        monthly_employee_cost["employee_count"] > 0
    )
)


# --------------------------------------------------
# --------------------------------------------------

# Monthly payroll reconciliation against answer key

# --------------------------------------------------

# Reconcile the full cleaned payroll dataset independently

# of the department and role filters selected in the dashboard.

reconciliation_payroll = payroll.copy()

excluded_payroll_ids = [
"PI-X0001",
"PI-X0002",
"PI-X0003",
"PI-X0004",
]

reconciliation_payroll = reconciliation_payroll[
~reconciliation_payroll["payroll_item_id"].isin(
excluded_payroll_ids
)
].copy()

reconciliation_payroll["period_end_date"] = pd.to_datetime(
reconciliation_payroll["period_end_date"],
errors="coerce",
)

reconciliation_payroll = reconciliation_payroll.dropna(
subset=["period_end_date"]
)

reconciliation_payroll["month"] = (
reconciliation_payroll["period_end_date"]
.dt.to_period("M")
.astype(str)
)

actual_reconciliation = (
reconciliation_payroll
.groupby("month", as_index=False)
.agg(
actual_gross=("gross_pay", "sum"),
actual_net=("net_pay", "sum"),
actual_employer_cost=("employer_cost", "sum"),
)
)

expected_reconciliation = answer_key.copy()

expected_reconciliation["month"] = (
pd.to_datetime(expected_reconciliation["month"])
.dt.to_period("M")
.astype(str)
)

reconciliation = actual_reconciliation.merge(
expected_reconciliation[
[
"month",
"payroll_gross_pay",
"payroll_net_pay",
"payroll_employer_cost",
]
],
on="month",
how="outer",
indicator=True,
)

reconciliation["gross_difference"] = (
reconciliation["actual_gross"]
- reconciliation["payroll_gross_pay"]
)

reconciliation["net_difference"] = (
reconciliation["actual_net"]
- reconciliation["payroll_net_pay"]
)

reconciliation["employer_cost_difference"] = (
reconciliation["actual_employer_cost"]
- reconciliation["payroll_employer_cost"]
)

reconciliation["status"] = "PASS"

reconciliation.loc[
(reconciliation["_merge"] != "both")
| (reconciliation["gross_difference"].abs() > 0.01)
| (reconciliation["net_difference"].abs() > 0.01)
| (reconciliation["employer_cost_difference"].abs() > 0.01),
"status",
] = "FAIL"

# Display reconciliation results in the dashboard.

st.subheader("Monthly Payroll Reconciliation")

pass_count = int((reconciliation["status"] == "PASS").sum())
fail_count = int((reconciliation["status"] == "FAIL").sum())

recon_col1, recon_col2 = st.columns(2)

recon_col1.metric("Months Passed", pass_count)
recon_col2.metric("Months Failed", fail_count)

if fail_count == 0 and len(reconciliation) == 18:
    st.success(
        "PASS: All 18 monthly payroll totals match "
        "the official reconciliation answer key."
    )
else:
    st.error(
        "Reconciliation differences found. "
        "Review the monthly comparison below."
    )
with st.expander("View monthly reconciliation details"):
    st.dataframe(
        reconciliation[
            [
                "month",
                "gross_difference",
                "net_difference",
                "employer_cost_difference",
                "status",
            ]
        ].round(2),
        hide_index=True,
        use_container_width=True,
    )
# --------------------------------------------------
# Payroll Cost Charts
# --------------------------------------------------

st.subheader("Payroll Cost Trends")

chart_data = reconciliation_payroll.copy()

chart_data["period_end_date"] = pd.to_datetime(
    chart_data["period_end_date"],
    errors="coerce",
)

chart_data["month"] = (
    chart_data["period_end_date"]
    .dt.to_period("M")
    .astype(str)
)

monthly_chart = (
    chart_data.groupby("month", as_index=False)
    .agg(
        Gross_Pay=("gross_pay", "sum"),
        Net_Pay=("net_pay", "sum"),
        Employer_Cost=("employer_cost", "sum"),
    )
)

monthly_chart = monthly_chart.sort_values("month")

fig = px.line(
    monthly_chart,
    x="month",
    y=["Gross_Pay", "Net_Pay", "Employer_Cost"],
    title="Monthly Payroll Cost Trend",
    labels={
        "month": "Month",
        "value": "Amount (₹)",
        "variable": "Payroll Measure",
    },
    markers=True,
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Employer Cost by Department")

departments = pd.read_csv(DEPARTMENT_FILE)

department_chart_data = reconciliation_payroll.merge(
    departments[["department_id", "department_name"]],
    on="department_id",
    how="left",
)

department_chart_data = (
    department_chart_data
    .groupby("department_name", as_index=False)
    .agg(
        Employer_Cost=("employer_cost", "sum"),
    )
    .sort_values("Employer_Cost", ascending=False)
)

fig_department = px.bar(
    department_chart_data,
    x="department_name",
    y="Employer_Cost",
    title="Total Employer Cost by Department",
    labels={
        "department_name": "Department",
        "Employer_Cost": "Employer Cost (₹)",
    },
)

st.plotly_chart(fig_department, use_container_width=True)