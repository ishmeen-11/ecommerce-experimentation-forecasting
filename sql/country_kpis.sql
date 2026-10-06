-- Revenue share by country
SELECT Country,
       ROUND(SUM(revenue), 2) AS revenue,
       COUNT(DISTINCT CustomerID) AS customers,
       ROUND(100 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1) AS revenue_share_pct
FROM tx GROUP BY Country ORDER BY revenue DESC
