from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Invoices, Receivables & Cash Flow",
    page_icon="💳",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "03_Data" / "csv"

REPORT_DATE = pd.Timestamp("2026-09-30")
CURRENCY = "₹"


# ---------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------
@st.cache_data
def load_data():
    invoices = pd.read_csv(DATA_DIR / "fact_invoice.csv")
    payments = pd.read_csv(DATA_DIR / "fact_invoice_payment.csv")
    clients = pd.read_csv(DATA_DIR / "dim_client.csv")
    ledger = pd.read_csv(DATA_DIR / "fact_ledger.csv")

    invoices["invoice_date"] = pd.to_datetime(invoices["invoice_date"])
    invoices["due_date"] = pd.to_datetime(invoices["due_date"])
    invoices["last_payment_date"] = pd.to_datetime(
        invoices["last_payment_date"], errors="coerce"
    )
    payments["payment_date"] = pd.to_datetime(payments["payment_date"])
    ledger["entry_date"] = pd.to_datetime(ledger["entry_date"])

    invoices["days_past_due_at_cutoff"] = pd.to_numeric(
    invoices["days_past_due_at_cutoff"], errors="coerce"
    ).fillna(0)

    for column in [
        "subtotal",
        "gst_amount",
        "total_amount",
        "amount_paid",
        "balance_due",
    ]:
        invoices[column] = pd.to_numeric(invoices[column], errors="coerce").fillna(0)

    payments["amount"] = pd.to_numeric(
        payments["amount"], errors="coerce"
    ).fillna(0)

    ledger["signed_amount_debit_positive"] = pd.to_numeric(
        ledger["signed_amount_debit_positive"], errors="coerce"
    ).fillna(0)

    return invoices, payments, clients, ledger


try:
    invoices, payments, clients, ledger = load_data()
except Exception as error:
    st.error(f"Unable to load the invoice and receivables data: {error}")
    st.stop()


# ---------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------
st.title("💳 Invoices, Receivables & Cash Flow Analytics")
st.caption(
    "Invoice performance, outstanding receivables, collections and "
    "accounts-receivable reconciliation | Reporting cutoff: 30 September 2026"
)

st.info(
    "Receivables are measured at the dataset cutoff date. "
    "Cash collections are calculated from payment transactions."
)
# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------
st.sidebar.header("Dashboard Filters")

client_options = ["All Clients"] + sorted(
    clients["client_id"].dropna().astype(str).unique().tolist()
)
selected_client = st.sidebar.selectbox("Client", client_options)

status_options = ["All Statuses"] + sorted(
    invoices["status"].dropna().astype(str).unique().tolist()
)
selected_status = st.sidebar.selectbox("Invoice Status", status_options)

date_min = invoices["invoice_date"].min().date()
date_max = invoices["invoice_date"].max().date()

date_range = st.sidebar.date_input(
    "Invoice Date Range",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = date_min, date_max

filtered_invoices = invoices[
    invoices["invoice_date"].between(
        pd.Timestamp(start_date), pd.Timestamp(end_date)
    )
].copy()

if selected_client != "All Clients":
    filtered_invoices = filtered_invoices[
        filtered_invoices["client_id"].astype(str) == selected_client
    ]

if selected_status != "All Statuses":
    filtered_invoices = filtered_invoices[
        filtered_invoices["status"] == selected_status
    ]


# ---------------------------------------------------------
# RECEIVABLES AND PAYMENT CALCULATIONS
# ---------------------------------------------------------
open_statuses = ["SENT", "OVERDUE", "PARTIALLY_PAID"]

open_invoices = filtered_invoices[
    filtered_invoices["status"].isin(open_statuses)
].copy()

overdue_invoices = open_invoices[
    open_invoices["days_past_due_at_cutoff"].fillna(0) > 0
].copy()

receivables_total = open_invoices["balance_due"].sum()
overdue_total = overdue_invoices["balance_due"].sum()

sent_total = open_invoices.loc[
    open_invoices["status"] == "SENT", "balance_due"
].sum()

partial_total = open_invoices.loc[
    open_invoices["status"] == "PARTIALLY_PAID", "balance_due"
].sum()

# Aggregate payment transactions by invoice before joining.
payment_by_invoice = (
    payments.groupby("invoice_id", as_index=False)
    .agg(transaction_paid=("amount", "sum"))
)

reconciliation = invoices[
    [
        "invoice_id",
        "invoice_number",
        "client_id",
        "total_amount",
        "amount_paid",
        "balance_due",
        "status",
    ]
].merge(payment_by_invoice, on="invoice_id", how="left")

reconciliation["transaction_paid"] = (
    reconciliation["transaction_paid"].fillna(0)
)
reconciliation["payment_difference"] = (
    reconciliation["amount_paid"] - reconciliation["transaction_paid"]
)

payment_exceptions = reconciliation[
    reconciliation["payment_difference"].abs() > 0.01
].copy()

# Account 1100 is Accounts Receivable.
ar_ledger = ledger[
    ledger["account_code"].astype(str).str.strip() == "1100"
].copy()

gl_closing_balance = ar_ledger[
    "signed_amount_debit_positive"
].sum()

subledger_closing_balance = invoices.loc[
    invoices["status"].isin(open_statuses), "balance_due"
].sum()

gl_reconciliation_difference = (
    gl_closing_balance - subledger_closing_balance
)
# ---------------------------------------------------------
# KPI SUMMARY
# ---------------------------------------------------------
st.subheader("Receivables Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Open Receivables",
    f"₹{receivables_total:,.0f}",
)
col2.metric(
    "Overdue Receivables",
    f"₹{overdue_total:,.0f}",
)
col3.metric(
    "Sent Invoices",
    f"₹{sent_total:,.0f}",
)
col4.metric(
    "Partially Paid",
    f"₹{partial_total:,.0f}",
)

st.caption(
    "Open receivables include SENT, OVERDUE and PARTIALLY_PAID invoices. "
    "DRAFT and CANCELLED invoices are excluded."
)


# ---------------------------------------------------------
# INVOICE STATUS ANALYSIS
# ---------------------------------------------------------
st.subheader("Invoice Status Analysis")

status_summary = (
    filtered_invoices.groupby("status", as_index=False)
    .agg(
        invoice_count=("invoice_id", "count"),
        invoice_value=("total_amount", "sum"),
        outstanding=("balance_due", "sum"),
    )
)

status_col1, status_col2 = st.columns(2)

with status_col1:
    fig_status = px.bar(
        status_summary,
        x="status",
        y="invoice_count",
        color="status",
        title="Invoice Count by Status",
        text_auto=True,
    )
    st.plotly_chart(fig_status, use_container_width=True)

with status_col2:
    fig_value = px.bar(
        status_summary,
        x="status",
        y="invoice_value",
        color="status",
        title="Invoice Value by Status",
        text_auto=".2s",
    )
    st.plotly_chart(fig_value, use_container_width=True)


# ---------------------------------------------------------
# MONTHLY INVOICE TREND
# ---------------------------------------------------------
st.subheader("Monthly Invoice Trend")

monthly_invoices = filtered_invoices.copy()
monthly_invoices["invoice_month"] = (
    monthly_invoices["invoice_date"].dt.to_period("M").astype(str)
)

monthly_invoice_summary = (
    monthly_invoices.groupby("invoice_month", as_index=False)
    .agg(
        invoice_value=("total_amount", "sum"),
        invoice_count=("invoice_id", "count"),
    )
)

fig_monthly_invoices = px.line(
    monthly_invoice_summary,
    x="invoice_month",
    y="invoice_value",
    markers=True,
    title="Monthly Invoice Value",
    labels={
        "invoice_month": "Invoice Month",
        "invoice_value": "Invoice Value (₹)",
    },
)
st.plotly_chart(fig_monthly_invoices, use_container_width=True)
# ---------------------------------------------------------

# ---------------------------------------------------------
# RECEIVABLE AGEING ANALYSIS
# ---------------------------------------------------------
st.subheader("Receivables Ageing")

ageing_invoices = open_invoices.copy()

# Assign invoices to the required ageing buckets
ageing_invoices["ageing_bucket"] = pd.cut(
    ageing_invoices["days_past_due_at_cutoff"].fillna(0),
    bins=[-float("inf"), 30, 60, 90, float("inf")],
    labels=["0-30 days", "31-60 days", "61-90 days", "90+ days"],
)

# Aggregate outstanding balances by ageing bucket
ageing_order = [
    "0-30 days",
    "31-60 days",
    "61-90 days",
    "90+ days",
]

ageing_summary = (
    ageing_invoices.groupby(
        "ageing_bucket",
        observed=False
    )
    .agg(
        outstanding=("balance_due", "sum"),
        invoice_count=("invoice_id", "count"),
    )
    .reindex(ageing_order, fill_value=0)
    .reset_index()
)
# ---------------------------------------------------------
# AGEING RECONCILIATION CHECK
# ---------------------------------------------------------

ageing_total = ageing_summary["outstanding"].sum()

receivables_total = open_invoices["balance_due"].sum()

ageing_difference = ageing_total - receivables_total

ageing_invoice_count = ageing_summary["invoice_count"].sum()

open_invoice_count = open_invoices["invoice_id"].count()

st.subheader("Ageing Reconciliation")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Total Open Receivables",
    f"₹{receivables_total:,.2f}"
)

col2.metric(
    "Total Ageing Outstanding",
    f"₹{ageing_total:,.2f}"
)

col3.metric(
    "Reconciliation Difference",
    f"₹{ageing_difference:,.2f}"
)

if abs(ageing_difference) < 0.01:
    st.success("PASS: Ageing balances reconcile with open receivables.")
else:
    st.error("WARNING: Ageing balances do not reconcile.")

if ageing_invoice_count == open_invoice_count:
    st.success(
        f"PASS: All {open_invoice_count} open invoices are included."
    )
else:
    st.warning(
        f"Invoice count mismatch: "
        f"{ageing_invoice_count} ageing invoices vs "
        f"{open_invoice_count} open invoices."
    )
fig_ageing = px.bar(
    ageing_summary,
    x="ageing_bucket",
    y="outstanding",
    color="ageing_bucket",
    title="Outstanding Receivables by Ageing Bucket",
    text_auto=".2s",
    labels={
        "ageing_bucket": "Ageing Bucket",
        "outstanding": "Outstanding (₹)",
    },
)

st.plotly_chart(fig_ageing, use_container_width=True)

st.caption(
    "Ageing is calculated using days past due at "
    "30 September 2026."
)


# ---------------------------------------------------------
# OVERDUE RECEIVABLES — METRIC M21
# ---------------------------------------------------------
st.subheader("Overdue Receivables")

# M21: unpaid invoice balance past due at the report date.
# Exclude only DRAFT and CANCELLED, following the metric dictionary.
m21_invoices = filtered_invoices[
    ~filtered_invoices["status"].isin(["DRAFT", "CANCELLED"])
    & (filtered_invoices["due_date"] < REPORT_DATE)
].copy()

m21_total = m21_invoices["balance_due"].sum()

st.metric("M21 — Overdue Receivables", f"₹{m21_total:,.0f}")

st.caption(
    "M21 follows the metric dictionary: due date before 30 September 2026, "
    "excluding DRAFT and CANCELLED statuses. A ₹100 negative-balance "
    "payment reconciliation exception is disclosed separately."
)

if not m21_invoices.empty:
    overdue_client_summary = (
        m21_invoices.groupby("client_id", as_index=False)
        .agg(
            overdue_amount=("balance_due", "sum"),
            invoice_count=("invoice_id", "count"),
        )
        .sort_values("overdue_amount", ascending=False)
        .head(10)
    )

    overdue_client_summary = overdue_client_summary.merge(
        clients[["client_id", "client_name"]],
        on="client_id",
        how="left",
    )

    fig_overdue_clients = px.bar(
        overdue_client_summary,
        x="client_name",
        y="overdue_amount",
        title="Top 10 Clients by Overdue Receivables",
        text_auto=".2s",
        labels={
            "client_name": "Client",
            "overdue_amount": "Overdue (₹)",
        },
    )
    st.plotly_chart(fig_overdue_clients, use_container_width=True)
else:
    st.info("No overdue invoices match the selected filters.")
# ---------------------------------------------------------
# ---------------------------------------------------------
# RECEIVABLES CONCENTRATION RISK
# ---------------------------------------------------------
st.subheader("Receivables Concentration Risk")

if not m21_invoices.empty and m21_total > 0:
    client_overdue_totals = (
        m21_invoices.groupby("client_id")["balance_due"]
        .sum()
        .sort_values(ascending=False)
    )

    largest_client_share = (
        client_overdue_totals.iloc[0] / m21_total
    ) * 100

    top_five_share = (
        client_overdue_totals.head(5).sum() / m21_total
    ) * 100

    col1, col2 = st.columns(2)

    col1.metric(
        "Largest Client Share of Overdue",
        f"{largest_client_share:.1f}%",
    )

    col2.metric(
        "Top 5 Clients Share of Overdue",
        f"{top_five_share:.1f}%",
    )
    if largest_client_share >= 30:
        st.warning(
            "High concentration risk: one client accounts for at least "
            "30% of overdue receivables."
        )
    elif top_five_share >= 70:
        st.warning(
            "Elevated concentration risk: the top five clients account "
            "for at least 70% of overdue receivables."
        )
    else:
        st.success(
            "No high customer concentration risk identified "
            "using these thresholds."
        )

else:
    st.info(
        "Customer concentration risk cannot be calculated because "
        "there are no positive overdue receivables."
    )
# ---------------------------------------------------------
# CLIENT PAYMENT BEHAVIOUR
# ---------------------------------------------------------
st.subheader("Client Payment Behaviour")

# Use fully paid invoices to calculate completed payment cycles.
paid_invoices = filtered_invoices[
    filtered_invoices["status"] == "PAID"
].copy()

paid_invoices["days_to_pay"] = pd.to_numeric(
    paid_invoices["days_to_pay"],
    errors="coerce"
)

paid_invoices = paid_invoices.dropna(
    subset=["days_to_pay"]
)

if not paid_invoices.empty:

    client_payment_summary = (
        paid_invoices.groupby("client_id", as_index=False)
        .agg(
            average_days_to_pay=("days_to_pay", "mean"),
            paid_invoice_count=("invoice_id", "count"),
        )
        .merge(
            clients[["client_id", "client_name"]],
            on="client_id",
            how="left",
        )
        .sort_values(
            "average_days_to_pay",
            ascending=False
        )
    )

    client_payment_summary["average_days_to_pay"] = (
        client_payment_summary["average_days_to_pay"].round(1)
    )

    st.caption(
        "Average payment time is calculated using fully paid "
        "invoices only. Partially paid and unpaid invoices are excluded."
    )

    st.dataframe(
        client_payment_summary[
            [
                "client_name",
                "average_days_to_pay",
                "paid_invoice_count",
            ]
        ].rename(
            columns={
                "client_name": "Client",
                "average_days_to_pay": "Average Days to Pay",
                "paid_invoice_count": "Paid Invoices",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # Highlight slow-paying clients.
    slow_payers = client_payment_summary[
        client_payment_summary["average_days_to_pay"] > 60
    ]

    if not slow_payers.empty:
        st.warning(
            f"{len(slow_payers)} clients take more than "
            "60 days on average to pay."
        )

        st.dataframe(
            slow_payers[
                [
                    "client_name",
                    "average_days_to_pay",
                    "paid_invoice_count",
                ]
            ].rename(
                columns={
                    "client_name": "Client",
                    "average_days_to_pay": "Average Days to Pay",
                    "paid_invoice_count": "Paid Invoices",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success(
            "No clients exceed the 60-day average payment threshold."
        )

    # Chart the ten slowest-paying clients.
    fig_payment_behaviour = px.bar(
        client_payment_summary.head(10).sort_values(
            "average_days_to_pay"
        ),
        x="average_days_to_pay",
        y="client_name",
        orientation="h",
        title="Top 10 Slowest-Paying Clients",
        labels={
            "average_days_to_pay": "Average Days to Pay",
            "client_name": "Client",
        },
    )

    st.plotly_chart(
        fig_payment_behaviour,
        use_container_width=True,
    )

else:
    st.info(
        "No fully paid invoices are available for payment "
        "behaviour analysis."
    )    
   # CASH COLLECTIONS
# ---------------------------------------------------------
st.subheader("Cash Collections")

filtered_invoice_ids = set(filtered_invoices["invoice_id"].astype(str))

filtered_payments = payments[
    payments["invoice_id"].astype(str).isin(filtered_invoice_ids)
].copy()

monthly_payments = filtered_payments.copy()
monthly_payments["payment_month"] = (
    monthly_payments["payment_date"].dt.to_period("M").astype(str)
)

monthly_collection_summary = (
    monthly_payments.groupby("payment_month", as_index=False)
    .agg(
        collections=("amount", "sum"),
        transaction_count=("payment_id", "count"),
    )
)

if not monthly_collection_summary.empty:
    fig_collections = px.bar(
        monthly_collection_summary,
        x="payment_month",
        y="collections",
        title="Monthly Cash Collections",
        text_auto=".2s",
        labels={
            "payment_month": "Payment Month",
            "collections": "Collections (₹)",
        },
    )
    st.plotly_chart(fig_collections, use_container_width=True)

    total_collections = filtered_payments["amount"].sum()
    st.metric("Cash Collected from Payment Transactions", f"₹{total_collections:,.0f}")
        # Month-over-month collection trend
    monthly_collection_summary = monthly_collection_summary.sort_values(
        "payment_month"
    )

    if len(monthly_collection_summary) >= 2:
        latest_month = monthly_collection_summary.iloc[-1]
        previous_month = monthly_collection_summary.iloc[-2]

        latest_collections = latest_month["collections"]
        previous_collections = previous_month["collections"]

        collection_change = latest_collections - previous_collections

        col1, col2 = st.columns(2)

        col1.metric(
            "Latest Month Collections",
            f"₹{latest_collections:,.0f}",
        )

        if previous_collections != 0:
            collection_change_pct = (
                collection_change / abs(previous_collections)
            ) * 100

            col2.metric(
                "Change vs Previous Month",
                f"₹{collection_change:,.0f}",
                delta=f"{collection_change_pct:+.1f}%",
            )
        else:
            col2.metric(
                "Change vs Previous Month",
                f"₹{collection_change:,.0f}",
                delta="Previous month was zero",
            )
    else:
        st.info(
            "At least two months of payment data are required "
            "for month-over-month comparison."
        )
else:
    st.info("No payment transactions match the selected invoice filters.")


# ---------------------------------------------------------
# PAYMENT MODE ANALYSIS
# ---------------------------------------------------------
st.subheader("Collections by Payment Mode")

if not filtered_payments.empty:
    payment_mode_summary = (
        filtered_payments.groupby("payment_mode", as_index=False)
        .agg(
            collections=("amount", "sum"),
            transaction_count=("payment_id", "count"),
        )
        .sort_values("collections", ascending=False)
    )

    fig_payment_modes = px.pie(
        payment_mode_summary,
        names="payment_mode",
        values="collections",
        hole=0.45,
        title="Cash Collections by Payment Mode",
    )
    st.plotly_chart(fig_payment_modes, use_container_width=True)
else:
    st.info("No payment mode data is available for the selected filters.")
    # ---------------------------------------------------------
# MONTHLY CASH IN VS CASH OUT
# ---------------------------------------------------------
st.subheader("Monthly Cash In vs Cash Out")

st.caption(
    "Company-wide cash movements from Bank - Operating Account "
    "and Petty Cash. Opening balances are excluded."
)

# Identify bank and petty cash ledger entries.
cash_ledger = ledger[
    ledger["account_code"].astype(str).str.strip().isin(["1001", "1002"])
].copy()

# Exclude opening balances and entries after the reporting cutoff.
cash_ledger = cash_ledger[
    (cash_ledger["source_type"] != "OPENING")
    & (cash_ledger["entry_date"] <= REPORT_DATE)
].copy()

if not cash_ledger.empty:

    cash_ledger["debit"] = pd.to_numeric(
        cash_ledger["debit"], errors="coerce"
    ).fillna(0)

    cash_ledger["credit"] = pd.to_numeric(
        cash_ledger["credit"], errors="coerce"
    ).fillna(0)

    cash_ledger["cash_month"] = (
        cash_ledger["entry_date"].dt.to_period("M").astype(str)
    )

    cash_flow_summary = (
        cash_ledger.groupby("cash_month", as_index=False)
        .agg(
            cash_in=("debit", "sum"),
            cash_out=("credit", "sum"),
        )
        .sort_values("cash_month")
    )

    cash_flow_summary["net_cash_flow"] = (
        cash_flow_summary["cash_in"]
        - cash_flow_summary["cash_out"]
    )

    # Display cash flow summary metrics.
    total_cash_in = cash_flow_summary["cash_in"].sum()
    total_cash_out = cash_flow_summary["cash_out"].sum()
    net_cash_flow = total_cash_in - total_cash_out

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Cash In", f"₹{total_cash_in:,.0f}")
    col2.metric("Total Cash Out", f"₹{total_cash_out:,.0f}")
    col3.metric("Net Cash Movement", f"₹{net_cash_flow:,.0f}")

    # Monthly comparison chart.
    fig_cash_flow = px.bar(
        cash_flow_summary,
        x="cash_month",
        y=["cash_in", "cash_out"],
        barmode="group",
        title="Monthly Cash In vs Cash Out",
        labels={
            "cash_month": "Month",
            "value": "Amount (₹)",
            "variable": "Cash Movement",
        },
        text_auto=".2s",
    )

    fig_cash_flow.update_layout(
        legend_title="Cash Movement",
        xaxis_title="Month",
        yaxis_title="Amount (₹)",
    )

    st.plotly_chart(
        fig_cash_flow,
        use_container_width=True,
    )

    # Monthly cash flow detail.
    st.dataframe(
        cash_flow_summary.rename(
            columns={
                "cash_month": "Month",
                "cash_in": "Cash In (₹)",
                "cash_out": "Cash Out (₹)",
                "net_cash_flow": "Net Cash Flow (₹)",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info("No cash ledger movements are available.")
# ---------------------------------------------------------
# PAYMENT RECONCILIATION
# ---------------------------------------------------------
st.subheader("Invoice vs Payment Transaction Reconciliation")

if not payment_exceptions.empty:
    st.warning(
        f"{len(payment_exceptions)} invoice(s) have a difference between "
        "the invoice-level amount_paid and the payment transaction total."
    )

    exception_display = payment_exceptions[
        [
            "invoice_number",
            "client_id",
            "total_amount",
            "amount_paid",
            "transaction_paid",
            "payment_difference",
            "balance_due",
            "status",
        ]
    ].copy()

    exception_display = exception_display.rename(
        columns={
            "invoice_number": "Invoice Number",
            "client_id": "Client ID",
            "total_amount": "Invoice Total (₹)",
            "amount_paid": "Invoice Amount Paid (₹)",
            "transaction_paid": "Payment Transactions (₹)",
            "payment_difference": "Difference (₹)",
            "balance_due": "Balance Due (₹)",
            "status": "Status",
        }
    )

    st.dataframe(exception_display, use_container_width=True, hide_index=True)
else:
    st.success("Invoice-level paid amounts match payment transactions.")


# ---------------------------------------------------------
# GENERAL LEDGER RECONCILIATION
# ---------------------------------------------------------
st.subheader("Accounts Receivable: GL vs Invoice Subledger")

gl_col1, gl_col2, gl_col3 = st.columns(3)

gl_col1.metric(
    "GL Account 1100 Closing Balance",
    f"₹{gl_closing_balance:,.0f}",
)

gl_col2.metric(
    "Invoice Subledger Open Balance",
    f"₹{subledger_closing_balance:,.0f}",
)

gl_col3.metric(
    "Reconciliation Difference",
    f"₹{gl_reconciliation_difference:,.0f}",
)

if abs(gl_reconciliation_difference) < 0.01:
    st.success(
        "The Accounts Receivable general-ledger closing balance "
        "matches the open invoice subledger."
    )
else:
    st.error(
        "The Accounts Receivable general-ledger balance does not "
        "match the open invoice subledger."
    )

st.caption(
    "GL balance uses account code 1100 (Accounts Receivable) and "
    "signed_amount_debit_positive. The subledger includes SENT, "
    "OVERDUE and PARTIALLY_PAID invoices."
)
# ---------------------------------------------------------
# DATA QUALITY EXCEPTION
# ---------------------------------------------------------
st.subheader("Data Quality: Payment Reconciliation Exception")

st.warning(
    "One ₹100 payment reconciliation exception was identified in the source data."
)

st.markdown(
    """
    - **Invoice:** INV/2025-26/0334 (INV-00385)
    - **Client:** CL-016
    - **Invoice total:** ₹1,049,728
    - **Payment transaction:** ₹1,049,728
    - **Invoice-level amount paid:** ₹1,049,828
    - **Recorded balance due:** -₹100
    - **Payment date:** 19 March 2026
    - **Payment mode:** NEFT

    The payment transaction matches the invoice total. The invoice-level
    `amount_paid` is ₹100 higher, producing a negative balance. The source
    data has not been altered; this exception is disclosed for investigation.
    """
)


# ---------------------------------------------------------
# KEY FINDINGS
# ---------------------------------------------------------
st.subheader("Key Findings")

st.markdown(
    f"""
    1. **Open receivables:** ₹{receivables_total:,.0f} across the
       selected invoice records.
    2. **Overdue exposure:** ₹{overdue_total:,.0f} across open invoices
       past their due date at the 30 September 2026 reporting cutoff.
    3. **Cash collections:** Payment transaction records are used
       to measure collections, avoiding invoice-level double counting.
    4. **GL reconciliation:** The difference between GL account 1100
       and the open invoice subledger is ₹{gl_reconciliation_difference:,.0f}.
    5. **Data quality:** One ₹100 invoice/payment reconciliation
       exception requires investigation.
    """
)


# ---------------------------------------------------------
# DATA NOTES
# ---------------------------------------------------------
with st.expander("Data Definitions and Methodology"):
    st.markdown(
        """
        - **Reporting cutoff:** 30 September 2026.
        - **Open receivables:** SENT, OVERDUE and PARTIALLY_PAID statuses.
        - **Excluded from open receivables:** DRAFT and CANCELLED.
        - **Ageing:** Calculated using `days_past_due_at_cutoff`
          at the reporting cutoff of 30 September 2026.
        - **Cash collections:** Sum of `fact_invoice_payment.amount`,
          grouped by payment date.
        - **M21 overdue receivables:** Invoice balances where due date
          is before the reporting cutoff, excluding DRAFT and CANCELLED.
        - **GL reconciliation:** Account code 1100 compared with the
          open invoice subledger.
        - **Known exception:** One ₹100 difference between invoice-level
          amount paid and payment transaction records.
        """
    )

st.caption(
    "PulseIQ | Invoices, Receivables & Cash Flow Analytics | "
    "Source: project CSV dataset"
)