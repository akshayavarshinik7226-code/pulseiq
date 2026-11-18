from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# PulseIQ | PQ-11 Profit & Loss and Expense Analytics
# --------------------------------------------------

st.set_page_config(
    page_title="PulseIQ | P&L and Expense Analytics",
    page_icon="📊",
    layout="wide",
)

st.title("Profit & Loss and Expense Analytics")
st.caption(
    "PQ-11 | Revenue, expenses, margin, expense categories, "
    "and top vendors"
)
# --------------------------------------------------
# File paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "03_Data" / "csv"

LEDGER_FILE = DATA_DIR / "fact_ledger.csv"
ACCOUNT_FILE = DATA_DIR / "dim_account.csv"
EXPENSE_FILE = DATA_DIR / "fact_expense.csv"
VENDOR_FILE = DATA_DIR / "dim_vendor.csv"

# --------------------------------------------------
# Load source data
# --------------------------------------------------


@st.cache_data
def load_data():
    ledger = pd.read_csv(LEDGER_FILE)
    accounts = pd.read_csv(ACCOUNT_FILE)
    expenses = pd.read_csv(EXPENSE_FILE)
    vendors = pd.read_csv(VENDOR_FILE)

    return ledger, accounts, expenses, vendors


ledger, accounts, expenses, vendors = load_data()
# --------------------------------------------------
# Prepare P&L detail accounts
# --------------------------------------------------

pnl_accounts = accounts[
    (accounts["is_group"] == "N")
    & (accounts["account_type"].isin(["INCOME", "EXPENSE"]))
].copy()

pnl_ledger = ledger.merge(
    pnl_accounts[
        [
            "account_code",
            "account_name",
            "account_type",
        ]
    ],
    on="account_code",
    how="inner",
)

pnl_ledger["amount"] = pnl_ledger[
    "signed_amount_debit_positive"
]

pnl_ledger.loc[
    pnl_ledger["account_type"] == "INCOME",
    "amount",
] = -pnl_ledger.loc[
    pnl_ledger["account_type"] == "INCOME",
    "amount",
]
# --------------------------------------------------
# Monthly P&L
# --------------------------------------------------

monthly_pnl = (
    pnl_ledger
    .groupby(["posting_period", "account_type"])["amount"]
    .sum()
    .unstack(fill_value=0)
    .reset_index()
)

monthly_pnl["Revenue"] = monthly_pnl.get("INCOME", 0)
monthly_pnl["Expenses"] = monthly_pnl.get("EXPENSE", 0)
monthly_pnl["Margin"] = (
    monthly_pnl["Revenue"] - monthly_pnl["Expenses"]
)

monthly_pnl["Margin %"] = (
    monthly_pnl["Margin"]
    / monthly_pnl["Revenue"]
    * 100
)
# --------------------------------------------------
# Month selector
# --------------------------------------------------

months = monthly_pnl["posting_period"].tolist()

selected_month = st.selectbox(
    "Select month",
    months,
    index=len(months) - 1,
)
# --------------------------------------------------
# Selected-month P&L summary
# --------------------------------------------------

selected_row = monthly_pnl[
    monthly_pnl["posting_period"] == selected_month
].iloc[0]

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Revenue",
    f"₹{selected_row['Revenue']:,.2f}",
)

col2.metric(
    "Expenses",
    f"₹{selected_row['Expenses']:,.2f}",
)

col3.metric(
    "Margin",
    f"₹{selected_row['Margin']:,.2f}",
)

col4.metric(
    "Margin %",
    f"{selected_row['Margin %']:.2f}%",
)

# --------------------------------------------------
# Monthly P&L trend
# --------------------------------------------------

st.subheader("Monthly Revenue, Expenses and Margin")

pnl_chart = monthly_pnl.melt(
    id_vars="posting_period",
    value_vars=["Revenue", "Expenses", "Margin"],
    var_name="Metric",
    value_name="Amount",
)

fig_pnl = px.line(
    pnl_chart,
    x="posting_period",
    y="Amount",
    color="Metric",
    markers=True,
    title="Monthly P&L Trend",
)

fig_pnl.update_layout(
    xaxis_title="Month",
    yaxis_title="Amount (₹)",
    legend_title="Metric",
)

st.plotly_chart(fig_pnl, use_container_width=True)
# --------------------------------------------------
# Selected-month P&L table
# --------------------------------------------------

st.subheader(f"P&L Detail — {selected_month}")

selected_pnl = monthly_pnl[
    monthly_pnl["posting_period"] == selected_month
][
    ["posting_period", "Revenue", "Expenses", "Margin", "Margin %"]
].copy()

st.dataframe(
    selected_pnl.style.format(
        {
            "Revenue": "₹{:,.2f}",
            "Expenses": "₹{:,.2f}",
            "Margin": "₹{:,.2f}",
            "Margin %": "{:.2f}%",
        }
    ),
    use_container_width=True,
    hide_index=True,
)
# --------------------------------------------------
# Expense by category
# --------------------------------------------------

expense_by_category = (
    pnl_ledger[
        pnl_ledger["account_type"] == "EXPENSE"
    ]
    .groupby(["account_code", "account_name"])["amount"]
    .sum()
    .reset_index()
    .sort_values("amount", ascending=False)
)

st.subheader("Expense by Category")

fig_expense_category = px.bar(
    expense_by_category,
    x="amount",
    y="account_name",
    orientation="h",
    title="Expense by Category",
    labels={
        "amount": "Expense Amount (₹)",
        "account_name": "Expense Category",
    },
)

fig_expense_category.update_layout(
    yaxis={"categoryorder": "total ascending"},
)

st.plotly_chart(
    fig_expense_category,
    use_container_width=True,
)
# --------------------------------------------------
# Top 10 vendors
# --------------------------------------------------

vendor_expense = expenses.merge(
    vendors[["vendor_id", "vendor_name"]],
    on="vendor_id",
    how="left",
)

top_vendors = (
    vendor_expense
    .groupby(["vendor_id", "vendor_name"])["total_amount"]
    .sum()
    .reset_index()
    .sort_values("total_amount", ascending=False)
    .head(10)
)

st.subheader("Top 10 Vendors by Expense")

fig_top_vendors = px.bar(
    top_vendors.sort_values("total_amount"),
    x="total_amount",
    y="vendor_name",
    orientation="h",
    title="Top 10 Vendors by Total Expense",
    labels={
        "total_amount": "Total Expense (₹)",
        "vendor_name": "Vendor",
    },
)

st.plotly_chart(
    fig_top_vendors,
    use_container_width=True,
)
# --------------------------------------------------
# Key findings
# --------------------------------------------------

st.subheader("Key Findings")

st.write(
    "• April 2026 had the highest monthly revenue at "
    "₹83,447,700.00 and also the highest monthly expenses "
    "at ₹71,999,728.50."
)

st.write(
    "• August 2026 had the highest monthly margin at "
    "₹22,126,646.76, with a margin of 27.16%."
)

st.write(
    "• July 2025 had the lowest margin percentage at 8.27%, "
    "while Skyline Realty Holdings was the highest-spend vendor "
    "over the full expense period at ₹19,917,739.20."
)