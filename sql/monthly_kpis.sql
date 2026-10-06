-- Monthly KPIs with month-over-month revenue growth
WITH m AS (
  SELECT DATE_TRUNC('month', date)          AS month,
         SUM(revenue)                       AS revenue,
         COUNT(DISTINCT InvoiceNo)          AS orders,
         COUNT(DISTINCT CustomerID)         AS customers
  FROM tx GROUP BY 1
)
SELECT DATE(month) AS month,
       ROUND(revenue, 2) AS revenue, orders, customers,
       ROUND(revenue / orders, 2) AS aov,
       ROUND(100 * (revenue / LAG(revenue) OVER (ORDER BY month) - 1), 1) AS mom_growth_pct
FROM m ORDER BY month
