-- PQ-04: Governed Metric Layer

CREATE VIEW m01_headcount AS SELECT month_start_date, department_id, headcount_end AS headcount FROM raw.fact_headcount_monthly WHERE (headcount_end >= 5);

CREATE VIEW m02_hires AS SELECT month_start_date, department_id, hires FROM raw.fact_headcount_monthly WHERE (headcount_end >= 5);

CREATE VIEW m03_exits AS SELECT month_start_date, department_id, exits FROM raw.fact_headcount_monthly WHERE (headcount_end >= 5);

CREATE VIEW m04_attrition_rate_monthly AS SELECT month_start_date, department_id, round(((100.0 * exits) / "nullif"(headcount_start, 0)), 2) AS attrition_rate_pct FROM raw.fact_headcount_monthly WHERE (headcount_start >= 10);

CREATE VIEW m05_attrition_rate_rolling_12m AS SELECT month_start_date, department_id, round(((100.0 * sum(exits) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)) / "nullif"(avg(headcount_end) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW), 0)), 2) AS attrition_rate_pct FROM raw.fact_headcount_monthly QUALIFY ((count() OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) = 12) AND (avg(headcount_end) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) >= 10));

CREATE VIEW m06_voluntary_attrition_rate AS SELECT month_start_date, department_id, round(((100.0 * sum(voluntary_exits) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)) / "nullif"(avg(headcount_end) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW), 0)), 2) AS voluntary_attrition_rate_pct FROM raw.fact_headcount_monthly QUALIFY ((count() OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) = 12) AND (avg(headcount_end) OVER (PARTITION BY department_id ORDER BY month_start_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) >= 10));

CREATE VIEW m07_gross_pay AS SELECT period_end_date, employee_id, gross_pay FROM raw.fact_payroll;

CREATE VIEW m08_net_pay AS SELECT period_end_date, employee_id, net_pay FROM raw.fact_payroll;

CREATE VIEW m09_payroll_cost AS SELECT period_end_date, department_id, round(sum(employer_cost), 2) AS employer_cost FROM raw.fact_payroll GROUP BY period_end_date, department_id HAVING (count(DISTINCT employee_id) >= 5);

CREATE VIEW m10_cost_per_head AS SELECT period_end_date, department_id, round((sum(employer_cost) / "nullif"(count(DISTINCT employee_id), 0)), 2) AS cost_per_head FROM raw.fact_payroll GROUP BY period_end_date, department_id HAVING (count(DISTINCT employee_id) >= 5);

CREATE VIEW m11_overtime_share AS SELECT period_end_date, department_id, round(((100.0 * sum(overtime_pay)) / "nullif"(sum(employer_cost), 0)), 2) AS overtime_share_pct FROM raw.fact_payroll GROUP BY period_end_date, department_id HAVING (count(DISTINCT employee_id) >= 5);

CREATE VIEW m12_variable_pay_share AS SELECT period_end_date, department_id, round(((100.0 * sum(variable_pay)) / "nullif"(sum(gross_pay), 0)), 2) AS variable_pay_share_pct FROM raw.fact_payroll GROUP BY period_end_date, department_id HAVING (count(DISTINCT employee_id) >= 5);

CREATE VIEW m13_attendance_rate AS SELECT period_end_date, department_id, round(((sum(present_days) + (0.5 * sum(half_days_unpaid))) / "nullif"(sum(scheduled_days), 0)), 4) AS attendance_rate FROM raw.fact_attendance_monthly GROUP BY period_end_date, department_id HAVING (count(DISTINCT employee_id) >= 5);

CREATE VIEW m14_late_arrival_rate AS SELECT period_end_date, department_id, round((sum(late_arrivals) / "nullif"(sum(present_days), 0)), 4) AS late_arrival_rate FROM raw.fact_attendance_monthly GROUP BY period_end_date, department_id HAVING (count(DISTINCT employee_id) >= 5);

CREATE VIEW m15_leave_without_pay_days AS SELECT period_end_date, employee_id, round(sum(lop_days), 2) AS lop_days FROM raw.fact_payroll GROUP BY period_end_date, employee_id;

CREATE VIEW m16_revenue AS SELECT CAST(date_trunc('month', entry_date) AS DATE) AS month_start_date, round(-(sum(signed_amount_debit_positive)), 2) AS revenue FROM raw.fact_ledger WHERE (account_code BETWEEN 4001 AND 4004) GROUP BY 1;

CREATE VIEW m17_net_profit AS SELECT CAST(date_trunc('month', entry_date) AS DATE) AS month_start_date, round(-(sum(signed_amount_debit_positive)), 2) AS net_profit FROM raw.fact_ledger WHERE (account_code BETWEEN 4000 AND 5999) GROUP BY 1;

CREATE VIEW m18_operating_margin AS SELECT p.month_start_date, round(((100.0 * p.net_profit) / "nullif"(r.revenue, 0)), 2) AS operating_margin_pct FROM m17_net_profit AS p INNER JOIN m16_revenue AS r USING (month_start_date);

CREATE VIEW m19_payroll_pct_revenue AS WITH payroll AS (SELECT CAST(date_trunc('month', period_end_date) AS DATE) AS month_start_date, sum(employer_cost) AS payroll_cost FROM raw.fact_payroll GROUP BY 1)SELECT r.month_start_date, round(((100.0 * p.payroll_cost) / "nullif"(r.revenue, 0)), 2) AS payroll_pct_revenue FROM payroll AS p INNER JOIN m16_revenue AS r USING (month_start_date);

CREATE VIEW m20_days_sales_outstanding AS WITH monthly_revenue AS (SELECT CAST(date_trunc('month', entry_date) AS DATE) AS month_start_date, -(sum(signed_amount_debit_positive)) AS revenue FROM raw.fact_ledger WHERE (account_code BETWEEN 4001 AND 4004) GROUP BY 1), receivables AS (SELECT CAST(date_trunc('month', invoice_date) AS DATE) AS month_start_date, sum(balance_due) AS closing_receivables FROM raw.fact_invoice WHERE (status NOT IN ('DRAFT', 'CANCELLED')) GROUP BY 1)SELECT r.month_start_date, round(((90.0 * r.closing_receivables) / "nullif"(v.revenue, 0)), 2) AS dso_days FROM receivables AS r INNER JOIN monthly_revenue AS v USING (month_start_date);

CREATE VIEW m21_overdue_receivables AS SELECT due_date AS report_date, client_id, round(sum(balance_due), 2) AS overdue_receivables FROM raw.fact_invoice WHERE ((due_date < CURRENT_DATE) AND (status NOT IN ('DRAFT', 'CANCELLED')) AND (balance_due > 0)) GROUP BY due_date, client_id;

CREATE VIEW m22_task_completion_rate AS SELECT team_id, sprint_id, round(((100.0 * count_star() FILTER (WHERE (status = 'Done'))) / "nullif"(count_star() FILTER (WHERE (status != 'Cancelled')), 0)), 2) AS completion_rate_pct FROM raw.fact_task GROUP BY team_id, sprint_id HAVING (count_star() FILTER (WHERE (status != 'Cancelled')) >= 5);

CREATE VIEW m23_on_time_delivery_rate AS SELECT team_id, sprint_id, round(((100.0 * count_star() FILTER (WHERE (completed_on_time = 'Y'))) / "nullif"(count_star() FILTER (WHERE (status = 'Done')), 0)), 2) AS on_time_delivery_rate_pct FROM raw.fact_task GROUP BY team_id, sprint_id HAVING (count_star() FILTER (WHERE (status = 'Done')) >= 5);

CREATE VIEW m24_velocity AS SELECT team_id, sprint_id, sum(story_points) FILTER (WHERE (status = 'Done')) AS velocity FROM raw.fact_task GROUP BY team_id, sprint_id;

CREATE VIEW m25_average_cycle_time AS SELECT team_id, sprint_id, round(avg(cycle_time_days), 2) AS avg_cycle_time_days FROM raw.fact_task WHERE (status = 'Done') GROUP BY team_id, sprint_id HAVING (count_star() >= 5);

CREATE VIEW m26_anomaly_flag_rate AS SELECT CAST(date_trunc('month', period) AS DATE) AS month_start_date, source_dataset, round(((100.0 * count_star() FILTER (WHERE (flagged = 'Y'))) / "nullif"(count_star(), 0)), 2) AS anomaly_flag_rate_pct FROM raw.fact_anomaly GROUP BY 1, 2;

CREATE VIEW m27_high_risk_share AS SELECT as_of_date, department_id, round(((100.0 * count_star() FILTER (WHERE (risk_band = 'High'))) / "nullif"(count_star(), 0)), 2) AS high_risk_share_pct FROM raw.fact_attrition_risk GROUP BY as_of_date, department_id HAVING (count(DISTINCT employee_id) >= 10);

CREATE VIEW m28_forecast_error_mape AS SELECT f.forecast_month AS month_start_date, f.department_id, round((avg((abs((h.headcount_end - f.forecast_value)) / "nullif"(abs(h.headcount_end), 0))) * 100), 2) AS forecast_error_mape_pct FROM raw.fact_forecast AS f INNER JOIN raw.fact_headcount_monthly AS h ON (((f.forecast_month = h.month_start_date) AND (f.department_id = h.department_id))) WHERE ((lower(f.metric) ~~ '%headcount%') AND (h.headcount_end != 0)) GROUP BY f.forecast_month, f.department_id;

CREATE VIEW metric_catalog AS SELECT metric_id, metric_name, business_definition AS definition, source_table AS "source", owner_team AS "owner", grain, minimum_group_size, formula, unit, caveat FROM raw.metric_dictionary;

