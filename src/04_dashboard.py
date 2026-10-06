"""Step 4: Build a single-file interactive dashboard (Plotly) from the output tables."""
import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "outputs" / "tables"
monthly = pd.read_csv(T / "monthly_kpis.csv", parse_dates=["month"])
cohort = pd.read_csv(T / "cohort_retention.csv")
ab = json.loads((T / "ab_results.json").read_text())
abd = pd.read_csv(T / "ab_daily_conversion.csv", parse_dates=["timestamp"])
bt = pd.read_csv(T / "forecast_backtest.csv", parse_dates=["date"])
fm = json.loads((T / "forecast_metrics.json").read_text())
dq = json.loads((T / "data_quality.json").read_text())

BLUE, ORANGE, GREY = "#2a6fdb", "#e8743b", "#9aa3ad"
fig = make_subplots(rows=2, cols=2, vertical_spacing=0.16, horizontal_spacing=0.09,
    subplot_titles=("Monthly revenue (Dec 2011 is partial, through Dec 9)",
                    "Cohort retention: % of customers active N months after first order",
                    f"A/B test daily conversion: new page {ab['lift_pp']:+.2f} pp, p = {ab['p_value']}",
                    f"Revenue forecast back-test (ensemble MAPE {fm['ensemble']['MAPE']}% vs naive {fm['seasonal_naive']['MAPE']}%)"))

fig.add_bar(x=monthly.month, y=monthly.revenue, marker_color=BLUE, name="Revenue",
            hovertemplate="%{x|%b %Y}<br>£%{y:,.0f}<extra></extra>", row=1, col=1)

p = cohort[cohort.cohort < "2011-12-01"].pivot(index="cohort", columns="month_n", values="retention_pct")
p = p.drop(columns=0)
fig.add_heatmap(z=p.values, x=[f"M{c}" for c in p.columns], y=[c[:7] for c in p.index],
                colorscale="Blues", zmin=0, zmax=45, showscale=False,
                hovertemplate="Cohort %{y}, %{x}: %{z}%<extra></extra>", row=1, col=2)
fig.update_yaxes(autorange="reversed", row=1, col=2)

fig.add_scatter(x=abd.timestamp, y=abd.control*100, name="Control (old page)", line_color=GREY, row=2, col=1)
fig.add_scatter(x=abd.timestamp, y=abd.treatment*100, name="Treatment (new page)", line_color=ORANGE, row=2, col=1)

fig.add_scatter(x=bt.date, y=bt.actual, name="Actual revenue", mode="lines+markers", line_color="#222", row=2, col=2)
fig.add_scatter(x=bt.date, y=bt.ensemble, name="SARIMA+Prophet", line=dict(color=BLUE), row=2, col=2)
fig.add_scatter(x=bt.date, y=bt.seasonal_naive, name="Seasonal naive", line=dict(color=GREY, dash="dot"), row=2, col=2)

fig.update_yaxes(title_text="£", row=1, col=1); fig.update_yaxes(title_text="Conversion %", row=2, col=1)
fig.update_yaxes(title_text="£ / day", row=2, col=2)
fig.update_layout(template="plotly_white", height=820, legend=dict(orientation="h", y=-0.08),
                  margin=dict(t=60, l=50, r=20, b=40), font=dict(family="Inter, Arial", size=12))

m1c = cohort[(cohort.month_n == 1) & (cohort.cohort < "2011-12-01")]
m1 = 100 * m1c.active_customers.sum() / m1c.cohort_size.sum()
nov = monthly.loc[monthly.month == "2011-11-01", "revenue"].iloc[0]
base = monthly[(monthly.month >= "2011-01-01") & (monthly.month <= "2011-08-01")].revenue.mean()
kpis = [("Clean transactions", f"{dq['clean_rows']:,}"), ("Revenue (13 mo)", f"£{monthly.revenue.sum()/1e6:.1f}M"),
        ("Nov peak vs Jan-Aug avg", f"{nov/base:.1f}x"), ("Month-1 retention", f"{m1:.1f}%"),
        ("A/B decision", "Don't ship"), ("Forecast error cut", f"{fm['mape_reduction_vs_naive_pct']}%")]
cards = "".join(f'<div class="k"><div class="v">{v}</div><div class="l">{l}</div></div>' for l, v in kpis)
html = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>E-commerce Experimentation & Forecasting</title>
<style>body{{font-family:Inter,Arial,sans-serif;margin:0;padding:24px;background:#f7f8fa;color:#1d2330}}
h1{{font-size:22px;margin:0 0 4px}}p{{margin:0 0 16px;color:#5b6472}}
.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}}
.k{{background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.v{{font-size:22px;font-weight:700}}.l{{font-size:12px;color:#5b6472;margin-top:4px}}
.c{{background:#fff;border-radius:10px;padding:8px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}</style></head><body>
<h1>E-commerce Experimentation & Forecasting</h1>
<p>UK online retailer, Dec 2010 to Dec 2011 (541K raw transactions) and a 290K-user landing-page A/B test.</p>
<div class="g">{cards}</div><div class="c">{fig.to_html(full_html=False, include_plotlyjs=True)}</div></body></html>"""
(ROOT / "outputs" / "dashboard.html").write_text(html)
print("dashboard written")
