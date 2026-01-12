# Databricks notebook source
# MAGIC %md
# MAGIC # Supplier Metrics Write-back
# MAGIC
# MAGIC Reads supplier metrics from Neo4j and writes back to Databricks Delta tables.
# MAGIC Uses TLS-enabled Neo4j Spark Connector (neo4j+s protocol).
# MAGIC
# MAGIC Parameters:
# MAGIC - catalog: Unity Catalog name (optional)

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.types import *
from datetime import datetime

# Parameters
dbutils.widgets.text("catalog", "", "Unity Catalog name")
catalog_param = dbutils.widgets.get("catalog")

def _get_catalog_names():
    try:
        df = spark.sql("SHOW CATALOGS")
        names = []
        for r in df.collect():
            for attr in ("catalog_name", "catalog", "name"):
                if hasattr(r, attr):
                    names.append(getattr(r, attr))
                    break
        return names
    except Exception:
        return []

catalog_names = _get_catalog_names()
preferred_catalog = "neo4j_pipeline"
CATALOG = catalog_param or (preferred_catalog if preferred_catalog in catalog_names else (catalog_names[0] if catalog_names else preferred_catalog))
spark.sql(f"USE CATALOG {CATALOG}")
print(f"Using catalog: {CATALOG}")

# COMMAND ----------
# Get Neo4j credentials from Databricks secrets

try:
    neo4j_uri = dbutils.secrets.get(scope="pipeline-secrets", key="neo4j-uri")
    neo4j_username = dbutils.secrets.get(scope="pipeline-secrets", key="neo4j-username")
    neo4j_password = dbutils.secrets.get(scope="pipeline-secrets", key="neo4j-password")
    print("✅ Neo4j credentials loaded from secrets")
except Exception as e:
    print(f"❌ Error loading secrets: {e}")
    raise RuntimeError("FAILED: Missing Neo4j credentials")

# Convert to neo4j+s protocol for TLS
if neo4j_uri.startswith("neo4j://"):
    neo4j_uri = neo4j_uri.replace("neo4j://", "neo4j+s://")
    print("✅ Converted Neo4j URI to use TLS (neo4j+s).")

# COMMAND ----------
# Read supplier metrics from Neo4j

print("Reading supplier metrics from Neo4j...")

cypher_query = """
MATCH (s:Supplier)
OPTIONAL MATCH (s)-[:SUPPLIES]->(p:Product)
WITH s, 
     count(DISTINCT p) as product_count,
     count(DISTINCT p.category) as category_diversity
RETURN s.id as supplier_id,
       product_count,
       category_diversity,
       CASE 
         WHEN product_count = 0 THEN 1.0
         WHEN category_diversity = 0 THEN 0.8
         WHEN category_diversity = 1 THEN 0.5
         ELSE 0.2
       END as risk_score
"""

try:
    metrics_df = spark.read.format("org.neo4j.spark.DataSource") \
        .option("url", neo4j_uri) \
        .option("authentication.type", "basic") \
        .option("authentication.basic.username", neo4j_username) \
        .option("authentication.basic.password", neo4j_password) \
        .option("query", cypher_query) \
        .load()
    
    print(f"✅ Read {metrics_df.count()} supplier metrics from Neo4j")
except Exception as e:
    print(f"❌ Error reading from Neo4j: {e}")
    raise

# COMMAND ----------
# Enrich with provenance columns

extract_timestamp = datetime.now().isoformat()

metrics_enriched = metrics_df \
    .withColumn("updated_at", F.lit(extract_timestamp)) \
    .withColumn("source_system", F.lit("neo4j")) \
    .withColumn("extract_ts", F.lit(extract_timestamp)) \
    .select(
        "supplier_id",
        "product_count",
        "category_diversity",
        "risk_score",
        "updated_at",
        "source_system",
        "extract_ts"
    )

print(f"✅ Enriched metrics with provenance columns")

# COMMAND ----------
# Validate data quality

print("\n📊 Data Quality Validation:")
total_records = metrics_enriched.count()
print(f"  Total records: {total_records}")

# Check for nulls in key columns
null_checks = ["supplier_id", "product_count", "category_diversity", "risk_score"]
for col_name in null_checks:
    null_count = metrics_enriched.filter(F.col(col_name).isNull()).count()
    if null_count > 0:
        print(f"  ⚠️ WARNING: {null_count} null values in {col_name}")
    else:
        print(f"  ✅ No nulls in {col_name}")

# COMMAND ----------
# Write to Delta table

output_table = f"{CATALOG}.gold.supplier_metrics"

try:
    metrics_enriched.write \
        .format("delta") \
        .mode("overwrite") \
        .option("overwriteSchema", "true") \
        .saveAsTable(output_table)
    
    print(f"\n✅ Successfully wrote {total_records} supplier metrics to {output_table}")
except Exception as e:
    print(f"❌ Error writing to Delta: {e}")
    raise

# COMMAND ----------
# Summary

print("\n" + "="*60)
print("SUPPLIER METRICS WRITE-BACK SUMMARY")
print("="*60)
print(f"Source: Neo4j Aura")
print(f"Target: {output_table}")
print(f"Records: {total_records}")
print(f"Extract Timestamp: {extract_timestamp}")
print("="*60)

dbutils.notebook.exit(f"SUCCESS: Wrote {total_records} supplier metrics")
