CREATE OR REPLACE VIEW m31_average_headcount AS
SELECT AVG(monthly_headcount) AS average_headcount
FROM (
    SELECT
        month_start_date,
        SUM(headcount) AS monthly_headcount
    FROM m01_headcount
    GROUP BY month_start_date
) AS monthly;