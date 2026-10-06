-- Daily revenue, orders, customers and average order value
SELECT date,
       ROUND(SUM(revenue), 2)                       AS revenue,
       COUNT(DISTINCT InvoiceNo)                    AS orders,
       COUNT(DISTINCT CustomerID)                   AS customers,
       ROUND(SUM(revenue) / COUNT(DISTINCT InvoiceNo), 2) AS aov
FROM tx
GROUP BY date
ORDER BY date
