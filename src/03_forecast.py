"""Step 3: Forecast daily revenue (SARIMA, Prophet) with a walk-forward back-test vs. a seasonal-naive baseline."""
import json, logging, warnings
from pathlib import Path
import numpy as np, pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from prophet import Prophet

warnings.filterwarnings("ignore"); logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "tables"

d = pd.read_csv(OUT / "daily_kpis.csv", parse_dates=["date"])[["date", "revenue"]]
# Store does not trade on Saturdays -> model the trading-day series (6-day week)
d = d[d.date.dt.dayofweek != 5].reset_index(drop=True)
# Drop the partial final day and obvious holiday-closure gaps are already absent
y = np.log(d.revenue.values)
S, H, FOLDS = 6, 6, 8          # weekly season, 1-week horizon, 8 weekly folds (~2 months)
start = len(d) - H * FOLDS

rows = []
for k in range(FOLDS):
    cut = start + k * H
    tr, te = d.iloc[:cut], d.iloc[cut:cut + H]
    ytr = y[:cut]
    naive = d.revenue.values[cut - S:cut - S + len(te)]                      # same day last week
    sar = SARIMAX(ytr, order=(1, 1, 1), seasonal_order=(1, 0, 1, S)).fit(disp=False)
    sar_fc = np.exp(sar.forecast(len(te)))
    m = Prophet(weekly_seasonality=False, daily_seasonality=False, yearly_seasonality=False,
                changepoint_prior_scale=0.3)
    m.add_seasonality("trading_week", period=7, fourier_order=3)
    m.fit(pd.DataFrame({"ds": tr.date, "y": ytr}))
    pr_fc = np.exp(m.predict(pd.DataFrame({"ds": te.date})).yhat.values)
    for i, r in enumerate(te.itertuples()):
        rows.append({"fold": k, "date": r.date, "actual": r.revenue,
                     "seasonal_naive": naive[i], "sarima": sar_fc[i], "prophet": pr_fc[i]})

bt = pd.DataFrame(rows)
bt["ensemble"] = (bt.sarima + bt.prophet) / 2
bt.to_csv(OUT / "forecast_backtest.csv", index=False)

def mape(a, f): return float(np.mean(np.abs(a - f) / a) * 100)
def wape(a, f): return float(np.sum(np.abs(a - f)) / np.sum(a) * 100)
models = ["seasonal_naive", "sarima", "prophet", "ensemble"]
metrics = {m: {"MAPE": round(mape(bt.actual, bt[m]), 1), "WAPE": round(wape(bt.actual, bt[m]), 1)} for m in models}
best = min(models[1:], key=lambda m: metrics[m]["MAPE"])
metrics["best_model"] = best
metrics["mape_reduction_vs_naive_pct"] = round(100 * (1 - metrics[best]["MAPE"] / metrics["seasonal_naive"]["MAPE"]), 1)
metrics["backtest"] = f"{FOLDS} weekly walk-forward folds, {bt.date.min().date()} to {bt.date.max().date()}"
(OUT / "forecast_metrics.json").write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
