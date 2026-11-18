 # PQ-09: Payroll Cost Dashboard â€” Evidence



 ## 1. Objective



Build a payroll cost dashboard that reports gross pay, net pay, and employer cost by department and month. The dashboard includes monthly reconciliation, cost-per-employee analysis, and department-level cost comparisons.



 ## 2. Data Quality and Exclusions



The source payroll dataset contained 7,344 rows. Four identified problematic rows were excluded from the cleaned reporting dataset, leaving 7,340 payroll records.



The exclusions covered:



\* Two duplicate employee/run payroll records.

\* Two payroll records associated with employee IDs that were missing from the employee dimension.



The original source data was preserved. Exclusions were applied to the reporting dataset rather than silently changing the source records.



 ## 3. Validation Results



The payroll validator reported the following results:



| Validation measure                |          Result |

| --------------------------------- | --------------: |

| Clean payroll records             |           7,340 |

| Unique employees                  |             528 |

| Unique payroll item IDs           |           7,340 |

| Duplicate payroll item IDs        |               0 |

| Payroll months covered            |              18 |

| Gross pay                         | â‚¹849,626,960.27 |

| Net pay                           | â‚¹751,018,306.69 |

| Employer cost                     | â‚¹861,586,392.42 |

| Average monthly cost per employee |     â‚¹117,297.37 |



The average monthly cost per employee is displayed as â‚¹117,297 in the dashboard. The â‚¹0.37 difference is due to rounding.



 ## 4. Reconciliation



The dashboard compares monthly gross pay, net pay, and employer cost with the supplied reconciliation answer key.



The dashboard was verified to display 18 months passed and zero failed. Reconciliation is calculated independently of the department and role filters so that changing the displayed selection does not alter the overall reconciliation result.



 ## 5. Dashboard Features



The dashboard includes:



\* Gross pay, net pay, and employer cost measures.

\* Department and role filters.

\* Monthly payroll cost trend.

\* Total employer cost by department.

\* Monthly cost-per-employee analysis.

\* Reconciliation status and monthly comparison results.



 ## 6. Privacy



The dashboard is intended to present aggregate payroll information. Individual employee names and individual salary amounts must not be exposed in the dashboard's public-facing views or screenshots.



Any detailed employee-level validation output should remain restricted and must not be included in public documentation.



 ## 7. Testing Performed



The following checks were performed:



\* Executed `validate\_payroll.py` successfully.

\* Confirmed 7,340 cleaned payroll records.

\* Confirmed no duplicate payroll item IDs in the cleaned dataset.

\* Checked the overall payroll totals.

\* Checked monthly reconciliation results.

\* Verified department and role filters.

\* Verified that the monthly reconciliation result remained unchanged when filters were adjusted.

\* Confirmed that both payroll charts displayed correctly.



 ## 8. Known Limitation



The validator also contains exploratory analysis of payroll changes between March and April 2026. Those findings should be treated as descriptive observations and not as proof of a specific business cause without further investigation.



 ## 9. Deliverables



\* `pages/5\_Payroll\_Cost.py` â€” payroll dashboard.

\* `validate\_payroll.py` â€” payroll validation and analysis.

\* `docs/pq09\_payroll\_evidence.md` â€” evidence and testing summary.



This evidence document records the checks performed. It does not replace the final Phase 2 report or the official evaluation.




