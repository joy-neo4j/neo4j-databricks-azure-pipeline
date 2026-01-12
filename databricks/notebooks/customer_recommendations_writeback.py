# Databricks notebook source
# MAGIC %md
# MAGIC # Customer Recommendations Write-back
# MAGIC
# MAGIC Reads recommendation data from Neo4j and writes back to Databricks Delta tables.
# MAGIC Uses TLS-enabled Neo4j Spark Connector (neo4j+s protocol).
# MAGIC
# MAGIC Parameters:
# MAGIC - catalog: Unity Catalog name (optional)

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.window import Window
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
    print("✅ Converted Neo4j URI to TLS (neo4j+s)")

# COMMAND ----------
# Read customer recommendations from Neo4j
# Query: Find products frequently purchased together with customer's purchases

print("Reading customer recommendations from Neo4j...")

cypher_query = """
MATCH (c:Customer)-[:PURCHASED]->(p1:Product)
MATCH (other:Customer)-[:PURCHASED]->(p1)
MATCH (other)-[:PURCHASED]->(p2:Product)
WHERE c <> other AND NOT (c)-[:PURCHASED]->(p2)
WITH c.id as customer_id, p2.id as product_id, count(*) as frequency
ORDER BY customer_id, frequency DESC
RETURN customer_id, product_id, frequency
LIMIT 10000
"""

try:
    recommendations_df = spark.read.format("org.neo4j.spark.DataSource") \
        .option("url", neo4j_uri) \
        .option("authentication.type", "basic") \
        .option("authentication.basic.username", neo4j_username) \
        .option("authentication.basic.password", neo4j_password) \
        .option("query", cypher_query) \
        .load()
    
    print(f"✅ Read {recommendations_df.count()} recommendations from Neo4j")
except Exception as e:
    print(f"❌ Error reading from Neo4j: {e}")
    raise

# COMMAND ----------
# Transform and enrich with provenance columns

extract_timestamp = datetime.now().isoformat()

recommendations_enriched = recommendations_df \
    .withColumn("rank", F.row_number().over(
        Window.partitionBy("customer_id").orderBy(F.col("frequency").desc())
    )) \
    .withColumn("score", F.col("frequency")) \
    .withColumn("reason", F.lit("frequently_purchased_together")) \
    .withColumn("updated_at", F.lit(extract_timestamp)) \
    .withColumn("source_system", F.lit("neo4j")) \
    .withColumn("extract_ts", F.lit(extract_timestamp)) \
    .select(
        "customer_id",
        "product_id",
        "rank",
        "score",
        "reason",
        "updated_at",
        "source_system",
        "extract_ts"
    )

print(f"✅ Enriched recommendations with provenance columns")

# COMMAND ----------
# Validate data quality

print("\n📊 Data Quality Validation:")
total_records = recommendations_enriched.count()
print(f"  Total records: {total_records}")

# Check for nulls in key columns
null_checks = ["customer_id", "product_id", "rank", "score"]
for col_name in null_checks:
    null_count = recommendations_enriched.filter(F.col(col_name).isNull()).count()
    if null_count > 0:
        print(f"  ⚠️ WARNING: {null_count} null values in {col_name}")
    else:
        print(f"  ✅ No nulls in {col_name}")

# COMMAND ----------
# Write to Delta table

output_table = f"{CATALOG}.gold.customer_recommendations"

try:
    recommendations_enriched.write \
        .format("delta") \
        .mode("overwrite") \
        .option("overwriteSchema", "true") \
        .saveAsTable(output_table)
    
    print(f"\n✅ Successfully wrote {total_records} recommendations to {output_table}")
except Exception as e:
    print(f"❌ Error writing to Delta: {e}")
    raise

# COMMAND ----------
# Summary

print("\n" + "="*60)
print("CUSTOMER RECOMMENDATIONS WRITE-BACK SUMMARY")
print("="*60)
print(f"Source: Neo4j Aura")
print(f"Target: {output_table}")
print(f"Records: {total_records}")
print(f"Extract Timestamp: {extract_timestamp}")
print("="*60)

dbutils.notebook.exit(f"SUCCESS: Wrote {total_records} customer recommendations")
