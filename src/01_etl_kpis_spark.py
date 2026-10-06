"""Step 1: Clean 540K online-retail transactions with PySpark and build KPI tables with Spark SQL."""
from pathlib import Path
from pyspark.sql import SparkSession, functions as F

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

spark = (SparkSession.builder.appName("retail-etl").master("local[*]")
         .config("spark.sql.session.timeZone", "UTC").config("spark.ui.enabled", "false").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

raw = spark.read.csv(str(ROOT / "data" / "online_retail.csv"), header=True, inferSchema=True)
n_raw = raw.count()

tx = (raw
      .withColumn("ts", F.to_timestamp("InvoiceDate", "M/d/yyyy H:mm"))
      .withColumn("date", F.to_date("ts"))
      .withColumn("is_cancel", F.col("InvoiceNo").cast("string").startswith("C"))
      .withColumn("revenue", F.col("Quantity") * F.col("UnitPrice")))

# Data quality checks
dq = {
    "raw_rows": n_raw,
    "cancellations": tx.filter("is_cancel").count(),
    "missing_customer_id": tx.filter(F.col("CustomerID").isNull()).count(),
    "non_positive_qty_or_price": tx.filter((F.col("Quantity") <= 0) | (F.col("UnitPrice") <= 0)).count(),
    "duplicate_rows": n_raw - raw.dropDuplicates().count(),
}

# Purchases later reversed by a matching cancellation (same customer, item, quantity) are removed,
# otherwise e.g. a single 80,995-unit order cancelled the same day inflates revenue.
cancels = (tx.filter("is_cancel").select("CustomerID", "StockCode", (-F.col("Quantity")).alias("Quantity")).dropDuplicates())
dq["purchases_reversed_by_cancellation"] = tx.filter(~F.col("is_cancel")).join(cancels, ["CustomerID", "StockCode", "Quantity"], "left_semi").count()

clean = (tx.dropDuplicates()
           .filter(~F.col("is_cancel"))
           .join(cancels, ["CustomerID", "StockCode", "Quantity"], "left_anti")
           .filter((F.col("Quantity") > 0) & (F.col("UnitPrice") > 0))
           .filter(~F.col("StockCode").isin("POST", "DOT", "M", "BANK CHARGES", "AMAZONFEE", "CRUK", "D", "S", "PADS", "B")))
clean.cache()
dq["clean_rows"] = clean.count()
clean.createOrReplaceTempView("tx")

sql_dir = ROOT / "sql"
def run(name):
    q = (sql_dir / f"{name}.sql").read_text()
    df = spark.sql(q).toPandas()
    df.to_csv(OUT / f"{name}.csv", index=False)
    return df

daily = run("daily_kpis")
monthly = run("monthly_kpis")
country = run("country_kpis")
cohort = run("cohort_retention")

import json
(OUT / "data_quality.json").write_text(json.dumps(dq, indent=2))
print(json.dumps(dq, indent=2))
print(monthly.tail(13).to_string(index=False))
print(country.head(8).to_string(index=False))
spark.stop()
