

from pathlib import Path
import pandas as pd

file_path = (
    Path(__file__).parent.parent
    / "03_Data"
    / "csv"
    / "fact_payroll.csv"
)

df = pd.read_csv(file_path)



df["period_end_date"] = pd.to_datetime(
    df["period_end_date"],
    errors="coerce",
)

df["payroll_month"] = (
    df["period_end_date"]
    .dt.to_period("M")
    .astype(str)
)

excluded_ids = [
    "PI-X0002",
    "PI-X0004",
    "PI-X0001",
    "PI-X0003",
]

df = df[
    ~df["payroll_item_id"].isin(excluded_ids)
].copy()

print("\n--- DATA OVERVIEW ---")
print("Total records:", len(df))
print("Unique employees:", df["employee_id"].nunique())
print("Unique payroll items:", df["payroll_item_id"].nunique())
print("Unique payroll runs:", df["run_id"].nunique())

print("\n--- DUPLICATE PAYROLL ITEM IDs ---")
print(df["payroll_item_id"].duplicated().sum())

print("\n--- EMPLOYEE RECORDS PER MONTH ---")
records_per_employee_month = (
    df.groupby(["employee_id", "payroll_month"])
    .size()
)

print(records_per_employee_month.describe())

print("\nEmployee-month combinations with multiple records:")
print(
    records_per_employee_month[
        records_per_employee_month > 1
    ].head(20)
)

print("\n--- MONTHLY SUMMARY ---")
monthly = (
    df.groupby("payroll_month")
    .agg(
        payroll_records=("payroll_item_id", "count"),
        employees=("employee_id", "nunique"),
        gross_pay=("gross_pay", "sum"),
        net_pay=("net_pay", "sum"),
        employer_cost=("employer_cost", "sum"),
    )
    .reset_index()
)

print(monthly.to_string(index=False))

print("\n--- HEADCOUNT FLAG ---")
if "headcount_flag" in df.columns:
    print(df["headcount_flag"].value_counts(dropna=False))

print("\n--- PAYROLL TOTALS ---")
for col in ["gross_pay", "net_pay", "employer_cost"]:
    print(f"{col}: {df[col].sum():,.2f}")


print("\n--- ADDITIONAL PAYROLL CHECKS ---")

print("Total payroll records:", len(df))

print("Unique employees:", df["employee_id"].nunique())

print(
    "Unique payroll item IDs:",
    df["payroll_item_id"].nunique()
)

print(
    "Duplicate payroll item IDs:",
    df["payroll_item_id"].duplicated().sum()
)

print("\nRecords per employee per month:")

print(
    df.groupby(
        [
            "employee_id",
            df["period_end_date"].astype(str).str[:7],
        ]
    ).size().describe()
)

print("\nHeadcount flag counts:")

print(df["headcount_flag"].value_counts(dropna=False))

print("\nGross Pay:", f"₹{df['gross_pay'].sum():,.2f}")
print("Net Pay:", f"₹{df['net_pay'].sum():,.2f}")
print(
    "Employer Cost:",
    f"₹{df['employer_cost'].sum():,.2f}"
)


print("Total payroll records:", len(df))
print("Unique employees:", df["employee_id"].nunique())
print("Gross Pay:", f"₹{df['gross_pay'].sum():,.2f}")

print("\n--- MONTHLY COST PER EMPLOYEE ---")

monthly_check = (
    df.groupby(df["period_end_date"].dt.to_period("M"))
    .agg(
        employer_cost=("employer_cost", "sum"),
        employee_count=("employee_id", "nunique"),
    )
)

monthly_check["cost_per_employee"] = (
    monthly_check["employer_cost"]
    / monthly_check["employee_count"]
)

print(monthly_check.round(2).to_string())


print("\n--- FINAL COST PER EMPLOYEE VALIDATION ---")

monthly_check = (
df.groupby(df["period_end_date"].dt.to_period("M"))
.agg(
employer_cost=("employer_cost", "sum"),
employee_count=("employee_id", "nunique"),
)
)

monthly_check["cost_per_employee"] = (
monthly_check["employer_cost"] / monthly_check["employee_count"]
)

eligible_months = monthly_check[
monthly_check["employee_count"] >= 5
]

average_monthly_cost = eligible_months["cost_per_employee"].mean()

print("Eligible months:", len(eligible_months))
print(f"Average monthly cost per employee: ₹{average_monthly_cost:,.2f}")
print(f"Dashboard value: ₹117,297.00")
print(
"Difference: ₹"
f"{abs(average_monthly_cost - 117297):,.2f}"
)
print("\n--- MARCH VS APRIL 2026 PAYROLL COMPARISON ---")

df["payroll_month"] = df["period_end_date"].dt.strftime("%Y-%m")

comparison = (
df[df["payroll_month"].isin(["2026-03", "2026-04"])]
.groupby("payroll_month")
.agg(
employees=("employee_id", "nunique"),
gross_pay=("gross_pay", "sum"),
net_pay=("net_pay", "sum"),
employer_cost=("employer_cost", "sum"),
)
)

comparison["cost_per_employee"] = (
comparison["employer_cost"] / comparison["employees"]
)

print(comparison.round(2).to_string())
print("\n--- MARCH VS APRIL PAYROLL COMPONENTS ---")

component_columns = [
"basic",
"hra",
"conveyance",
"medical",
"special_allowance",
"earned_fixed_pay",
"overtime_pay",
"variable_pay",
"pf_employer",
"esi_employer",
"gross_pay",
"employer_cost",
]

component_check = (
df[df["payroll_month"].isin(["2026-03", "2026-04"])]
.groupby("payroll_month")[component_columns]
.sum()
.T
)

component_check["change_amount"] = (
component_check["2026-04"] - component_check["2026-03"]
)

component_check["change_percent"] = (
component_check["change_amount"]
/ component_check["2026-03"].replace(0, float("nan"))
* 100
)

print(component_check.round(2).to_string())

print("\n--- VARIABLE PAY BY TYPE: MARCH VS APRIL 2026 ---")

variable_check = (
    df[
        df["payroll_month"].isin(["2026-03", "2026-04"])
    ]
    .groupby(["payroll_month", "variable_pay_type"], dropna=False)
    .agg(
        records=("payroll_item_id", "count"),
        employees=("employee_id", "nunique"),
        variable_pay=("variable_pay", "sum"),
    )
    .reset_index()
)

print(
    variable_check.sort_values(
        ["payroll_month", "variable_pay"],
        ascending=[True, False],
    ).round(2).to_string(index=False)
)

print("\n--- APRIL 2026 PERFORMANCE BONUS DETAILS ---")

bonus = df[
    (df["payroll_month"] == "2026-04")
    & (df["variable_pay_type"] == "Performance Bonus")
].copy()

bonus_summary = (
    bonus.groupby("employee_id")
    .agg(
        bonus_amount=("variable_pay", "sum"),
        records=("payroll_item_id", "count"),
    )
    .sort_values("bonus_amount", ascending=False)
)

print("Employees receiving performance bonus:", bonus["employee_id"].nunique())
print("Total performance bonus:", round(bonus["variable_pay"].sum(), 2))
print("Average bonus per employee:", round(bonus_summary["bonus_amount"].mean(), 2))
print("Median bonus per employee:", round(bonus_summary["bonus_amount"].median(), 2))
print("\nTop 10 bonus amounts:")
print(bonus_summary.head(10).round(2).to_string())


print("\n--- APRIL PERFORMANCE BONUS COMPARISON ---")

april_bonus = df[
    (df["payroll_month"].isin(["2025-04", "2026-04"]))
    & (df["variable_pay_type"].notna())
].copy()

april_bonus_summary = (
    april_bonus.groupby(["payroll_month", "variable_pay_type"])
    .agg(
        employees=("employee_id", "nunique"),
        total_variable_pay=("variable_pay", "sum"),
    )
    .reset_index()
)

print(april_bonus_summary.round(2).to_string(index=False))

print("\n--- APRIL 2026 PERFORMANCE BONUS BY DEPARTMENT ---")

from pathlib import Path

department_file = (
    Path(__file__).parent.parent
    / "03_Data"
    / "csv"
    / "dim_department.csv"
)

departments = pd.read_csv(department_file)

april_department_bonus = df[
    (df["payroll_month"] == "2026-04")
    & (df["variable_pay_type"] == "Performance Bonus")
].copy()

department_summary = (
    april_department_bonus
    .groupby("department_id")
    .agg(
        employees=("employee_id", "nunique"),
        total_bonus=("variable_pay", "sum"),
    )
    .reset_index()
    .merge(departments, on="department_id", how="left")
)

# Apply the minimum group-size privacy threshold.
department_summary = department_summary[
    department_summary["employees"] >= 5
].copy()

department_summary["percentage_of_total"] = (
    department_summary["total_bonus"]
    / april_department_bonus["variable_pay"].sum()
    * 100
)
department_summary["average_bonus_per_employee"] = (
    department_summary["total_bonus"]
    / department_summary["employees"]
)

department_summary["share_of_bonus_recipients"] = (
    department_summary["employees"]
    / april_department_bonus["employee_id"].nunique()
    * 100
)
department_summary = department_summary.sort_values(
    "total_bonus", ascending=False
)

print(
    department_summary[
        [
            "department_name",
            "employees",
            "total_bonus",
            "average_bonus_per_employee",
            "percentage_of_total",
            "share_of_bonus_recipients",
        ]
    ].round(2).to_string(index=False)
)


# --- APRIL 2026 PERFORMANCE BONUS AS A PERCENTAGE OF GROSS PAY ---

april_payroll = df[df["payroll_month"] == "2026-04"].copy()

department_payroll = (
    april_payroll
    .groupby("department_id")
    .agg(
        employees=("employee_id", "nunique"),
        gross_pay=("gross_pay", "sum"),
    )
    .reset_index()
    .merge(departments, on="department_id", how="left")
)

department_analysis = department_summary.merge(
    department_payroll[["department_id", "gross_pay"]],
    on="department_id",
    how="left",
)

department_analysis["bonus_as_percentage_of_gross"] = (
    department_analysis["total_bonus"]
    / department_analysis["gross_pay"]
    * 100
)

department_analysis = department_analysis.sort_values(
    "bonus_as_percentage_of_gross",
    ascending=False,
)

print("\n--- APRIL 2026 BONUS AS A PERCENTAGE OF DEPARTMENT GROSS PAY ---")
print(
    department_analysis[
        [
            "department_name",
            "employees",
            "total_bonus",
            "gross_pay",
            "bonus_as_percentage_of_gross",
        ]
    ].round(2).to_string(index=False)
)

