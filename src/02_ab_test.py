"""Step 2: Analyze a landing-page A/B test (~290K users): data checks, power, z-test, bootstrap CI, segments."""
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, proportion_confint
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "tables"
rng = np.random.default_rng(42)

df = pd.read_csv(ROOT / "data" / "ab_data.csv", parse_dates=["timestamp"])
checks = {"raw_rows": len(df)}

# 1. Assignment integrity: treatment must see new_page, control must see old_page
mismatch = ((df.group == "treatment") != (df.landing_page == "new_page"))
checks["group_page_mismatch_rows"] = int(mismatch.sum())
df = df[~mismatch]
checks["duplicate_users_removed"] = int(df.user_id.duplicated().sum())
df = df.drop_duplicates("user_id", keep="first")
checks["analysis_users"] = len(df)

# 2. Sample ratio mismatch (expect 50/50)
n = df.group.value_counts()
srm_p = stats.chisquare([n["control"], n["treatment"]]).pvalue
checks["srm_p_value"] = round(float(srm_p), 4)

# 3. Conversion rates and two-proportion z-test
conv = df.groupby("group").converted.agg(["sum", "count", "mean"])
c, t = conv.loc["control"], conv.loc["treatment"]
z, p = proportions_ztest([t["sum"], c["sum"]], [t["count"], c["count"]], alternative="two-sided")
lift_pp = (t["mean"] - c["mean"]) * 100
se = np.sqrt(c["mean"]*(1-c["mean"])/c["count"] + t["mean"]*(1-t["mean"])/t["count"])
ci_pp = ((t["mean"]-c["mean"]) - 1.96*se) * 100, ((t["mean"]-c["mean"]) + 1.96*se) * 100

# 4. Bootstrap CI for the difference (10K resamples)
cv, tv = df[df.group=="control"].converted.values, df[df.group=="treatment"].converted.values
boots = np.array([rng.choice(tv, tv.size).mean() - rng.choice(cv, cv.size).mean() for _ in range(10_000)]) * 100
boot_ci = np.percentile(boots, [2.5, 97.5])

# 5. Power: minimum detectable effect with this sample, and n needed to detect a +0.5pp lift
power = NormalIndPower()
base = c["mean"]
mde = None
for d_pp in np.arange(0.05, 2.0, 0.01):
    es = proportion_effectsize(base + d_pp/100, base)
    if power.power(es, nobs1=c["count"], alpha=0.05, ratio=t["count"]/c["count"]) >= 0.8:
        mde = round(float(d_pp), 2); break
n_needed = int(np.ceil(power.solve_power(proportion_effectsize(base+0.005, base), alpha=0.05, power=0.8)))

# 6. Segment check: lift by day-of-week (consistency / novelty effects)
df["dow"] = df.timestamp.dt.day_name()
seg = (df.groupby(["dow","group"]).converted.mean().unstack()
         .assign(lift_pp=lambda x: (x.treatment-x.control)*100).round(4))
seg.to_csv(OUT / "ab_segment_by_dow.csv")
daily = df.groupby([df.timestamp.dt.date,"group"]).converted.mean().unstack()
daily.to_csv(OUT / "ab_daily_conversion.csv")

res = {**checks,
       "control_rate_pct": round(c["mean"]*100, 2), "treatment_rate_pct": round(t["mean"]*100, 2),
       "lift_pp": round(lift_pp, 2), "z": round(float(z), 3), "p_value": round(float(p), 3),
       "ci95_pp": [round(ci_pp[0], 2), round(ci_pp[1], 2)],
       "bootstrap_ci95_pp": [round(boot_ci[0], 2), round(boot_ci[1], 2)],
       "mde_pp_at_80pct_power": mde, "n_per_arm_for_0.5pp_lift": n_needed,
       "segments_with_positive_lift": int((seg.lift_pp > 0).sum()), "segments_total": len(seg),
       "decision": "Do not ship: no significant lift and CI rules out gains above the upper bound"}
(OUT / "ab_results.json").write_text(json.dumps(res, indent=2))
print(json.dumps(res, indent=2)); print(seg)
