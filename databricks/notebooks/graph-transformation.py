# Databricks notebook source
# MAGIC %md
# MAGIC # Graph Transformation (Silver → Graph Ready)
# MAGIC 
# MAGIC Transforms Silver tables into Neo4j-ready nodes and relationships.
# MAGIC 
# MAGIC Parameters:
# MAGIC - `catalog`: Unity Catalog name (optional)
# MAGIC 
# MAGIC Outputs (Graph Ready):
# MAGIC - {catalog}.graph_ready.customer_nodes
# MAGIC - {catalog}.graph_ready.product_nodes
# MAGIC - {catalog}.graph_ready.purchased_relationships
# MAGIC - {catalog}.graph_ready.reviewed_relationships

# COMMAND ----------

# MAGIC %pip install pyyaml

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *
import yaml

# Catalog resolution with optional override
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
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.graph_ready")

# COMMAND ----------
# Read Silver tables (fail fast with a clear message)

def must_table(t):
    try:
        df = spark.table(t)
        c = df.count()
        print(f"Loaded {c} rows from {t}")
        return df
    except Exception as e:
        raise RuntimeError(f"Missing required table {t}: {e}")

customers_df = must_table(f"{CATALOG}.silver.customers")
products_df  = must_table(f"{CATALOG}.silver.products")
orders_df    = must_table(f"{CATALOG}.silver.orders")
reviews_df   = must_table(f"{CATALOG}.silver.reviews")

# COMMAND ----------
# Build nodes (Graph Ready)

customer_nodes = customers_df.select(
    F.col("id").alias("node_id"),
    F.to_json(F.struct(
        F.col("name"),
        F.col("email"),
        F.col("age"),
        F.col("gender"),
        F.col("city"),
        F.col("country"),
        F.col("customer_segment"),
        F.col("preferences"),
        F.col("age_group")
    )).alias("properties")
).withColumn("label", F.lit("Customer"))

product_nodes = products_df.select(
    F.col("id").alias("node_id"),
    F.to_json(F.struct(
        F.col("name"),
        F.col("description"),
        F.col("category"),
        F.col("subcategory"),
        F.col("price"),
        F.col("stock_quantity"),
        F.col("price_tier"),
        F.col("in_stock")
    )).alias("properties")
).withColumn("label", F.lit("Product"))

# COMMAND ----------
# Build relationships (Graph Ready)

purchased_rels = orders_df.select(
    F.col("customer_id").alias("from_id"),
    F.col("product_id").alias("to_id"),
    F.to_json(F.struct(
        F.col("id").alias("order_id"),
        F.col("quantity"),
        F.col("total_amount"),
        F.col("order_date"),
        F.col("status"),
        F.col("payment_method")
    )).alias("properties")
).withColumn("rel_type", F.lit("PURCHASED"))

reviewed_rels = reviews_df.select(
    F.col("customer_id").alias("from_id"),
    F.col("product_id").alias("to_id"),
    F.to_json(F.struct(
        F.col("rating"),
        F.col("review_text"),
        F.col("review_date"),
        F.col("sentiment")
    )).alias("properties")
).withColumn("rel_type", F.lit("REVIEWED"))

# COMMAND ----------
# Write Graph Ready tables

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.graph_ready")

customer_nodes.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.graph_ready.customer_nodes")
print(f"✅ Wrote {customer_nodes.count()} → {CATALOG}.graph_ready.customer_nodes")

product_nodes.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.graph_ready.product_nodes")
print(f"✅ Wrote {product_nodes.count()} → {CATALOG}.graph_ready.product_nodes")

purchased_rels.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.graph_ready.purchased_relationships")
print(f"✅ Wrote {purchased_rels.count()} → {CATALOG}.graph_ready.purchased_relationships")

reviewed_rels.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.graph_ready.reviewed_relationships")
print(f"✅ Wrote {reviewed_rels.count()} → {CATALOG}.graph_ready.reviewed_relationships")

# COMMAND ----------
# Summary and Exit

print("\n" + "="*60)
print("GRAPH READY SUMMARY")
print("="*60)
print(f"Customer Nodes: {customer_nodes.count()}")
print(f"Product Nodes:  {product_nodes.count()}")
print(f"PURCHASED Rels: {purchased_rels.count()}")
print(f"REVIEWED Rels:  {reviewed_rels.count()}")

dbutils.notebook.exit("SUCCESS: Graph Ready data prepared")
