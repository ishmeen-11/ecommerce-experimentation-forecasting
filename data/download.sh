#!/usr/bin/env bash
# Downloads both public datasets into data/
set -e; cd "$(dirname "$0")"
curl -sSL -o online_retail.csv https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv
curl -sSL -o ab_data.csv https://raw.githubusercontent.com/hwangmpaula/Analyze-A-B-Test-Results/master/ab_data.csv
echo "done"
