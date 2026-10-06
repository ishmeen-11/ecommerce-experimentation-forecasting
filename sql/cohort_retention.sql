-- Monthly acquisition cohorts: % of customers who purchase again N months after first purchase
WITH cust AS (
  SELECT CustomerID, DATE_TRUNC('month', date) AS order_month
  FROM tx WHERE CustomerID IS NOT NULL GROUP BY 1, 2
),
first AS (
  SELECT CustomerID, MIN(order_month) AS cohort FROM cust GROUP BY 1
),
joined AS (
  SELECT f.cohort, c.CustomerID,
         CAST(MONTHS_BETWEEN(c.order_month, f.cohort) AS INT) AS month_n
  FROM cust c JOIN first f USING (CustomerID)
),
sizes AS (SELECT cohort, COUNT(DISTINCT CustomerID) AS cohort_size FROM first GROUP BY 1)
SELECT DATE(j.cohort) AS cohort, s.cohort_size, j.month_n,
       COUNT(DISTINCT j.CustomerID) AS active_customers,
       ROUND(100 * COUNT(DISTINCT j.CustomerID) / s.cohort_size, 1) AS retention_pct
FROM joined j JOIN sizes s USING (cohort)
GROUP BY 1, 2, 3 ORDER BY 1, 3
