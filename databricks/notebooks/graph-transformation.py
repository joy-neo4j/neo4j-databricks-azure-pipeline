# Databricks notebook source
# MAGIC %md
# MAGIC # Graph Transformation Notebook
# MAGIC 
# MAGIC This notebook transforms relational data from Silver layer into graph-ready format in Gold layer.
# MAGIC 
# MAGIC **Graph Schema:**
# MAGIC - Nodes: Customer, Product, Order
# MAGIC - Relationships: PLACED_ORDER, CONTAINS_PRODUCT
# MAGIC 
# MAGIC **Parameters:**
# MAGIC - `environment`: Target environment

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.window import Window
import yaml

# Get parameters
dbutils.widgets.text("environment", "dev", "Environment")
environment = dbutils.widgets.get("environment")

print(f"Environment: {environment}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Data from Silver Layer

# COMMAND ----------

# Read Silver tables
customers_df = spark.table(f"neo4j_pipeline_{environment}.silver.customers")
products_df = spark.table(f"neo4j_pipeline_{environment}.silver.products")
orders_df = spark.table(f"neo4j_pipeline_{environment}.silver.orders")

print(f"Customers: {customers_df.count()}")
print(f"Products: {products_df.count()}")
print(f"Orders: {orders_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform to Graph Nodes

# COMMAND ----------

# Customer Nodes
customer_nodes = customers_df.select(
    F.col("id").alias("node_id"),
    F.lit("Customer").alias("node_label"),
    F.to_json(F.struct(
        F.col("name"),
        F.col("email"),
        F.col("created_at")
    )).alias("properties"),
    F.current_timestamp().alias("transform_timestamp")
)

print(f"\nCustomer nodes: {customer_nodes.count()}")
customer_nodes.show(5, truncate=False)

# COMMAND ----------

# Product Nodes
product_nodes = products_df.select(
    F.col("id").alias("node_id"),
    F.lit("Product").alias("node_label"),
    F.to_json(F.struct(
        F.col("name"),
        F.col("category"),
        F.col("price"),
        F.col("created_at")
    )).alias("properties"),
    F.current_timestamp().alias("transform_timestamp")
)

print(f"\nProduct nodes: {product_nodes.count()}")
product_nodes.show(5, truncate=False)

# COMMAND ----------

# Order Nodes
order_nodes = orders_df.select(
    F.col("id").alias("node_id"),
    F.lit("Order").alias("node_label"),
    F.to_json(F.struct(
        F.col("order_date"),
        F.col("total_amount")
    )).alias("properties"),
    F.current_timestamp().alias("transform_timestamp")
)

print(f"\nOrder nodes: {order_nodes.count()}")
order_nodes.show(5, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform to Graph Relationships

# COMMAND ----------

# Customer PLACED_ORDER Relationship
placed_order_rels = orders_df.select(
    F.concat(F.lit("customer_"), F.col("customer_id"), F.lit("_order_"), F.col("id")).alias("relationship_id"),
    F.lit("PLACED_ORDER").alias("relationship_type"),
    F.col("customer_id").alias("source_node_id"),
    F.lit("Customer").alias("source_node_label"),
    F.col("id").alias("target_node_id"),
    F.lit("Order").alias("target_node_label"),
    F.to_json(F.struct(
        F.col("order_date")
    )).alias("properties"),
    F.current_timestamp().alias("transform_timestamp")
)

print(f"\nPLACED_ORDER relationships: {placed_order_rels.count()}")
placed_order_rels.show(5, truncate=False)

# COMMAND ----------

# Order CONTAINS_PRODUCT Relationship
contains_product_rels = orders_df.select(
    F.concat(F.lit("order_"), F.col("id"), F.lit("_product_"), F.col("product_id")).alias("relationship_id"),
    F.lit("CONTAINS_PRODUCT").alias("relationship_type"),
    F.col("id").alias("source_node_id"),
    F.lit("Order").alias("source_node_label"),
    F.col("product_id").alias("target_node_id"),
    F.lit("Product").alias("target_node_label"),
    F.to_json(F.struct(
        F.col("quantity")
    )).alias("properties"),
    F.current_timestamp().alias("transform_timestamp")
)

print(f"\nCONTAINS_PRODUCT relationships: {contains_product_rels.count()}")
contains_product_rels.show(5, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Combine All Nodes and Relationships

# COMMAND ----------

# Union all nodes
all_nodes = customer_nodes \
    .union(product_nodes) \
    .union(order_nodes)

print(f"\nTotal nodes: {all_nodes.count()}")

# Union all relationships
all_relationships = placed_order_rels \
    .union(contains_product_rels)

print(f"Total relationships: {all_relationships.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Add Graph Metrics

# COMMAND ----------

# Add node degree (number of relationships)
node_degrees = all_relationships \
    .groupBy("source_node_id") \
    .agg(F.count("*").alias("out_degree")) \
    .union(
        all_relationships
        .groupBy("target_node_id")
        .agg(F.count("*").alias("in_degree"))
        .withColumnRenamed("target_node_id", "source_node_id")
        .withColumnRenamed("in_degree", "out_degree")
    ) \
    .groupBy("source_node_id") \
    .agg(F.sum("out_degree").alias("total_degree"))

# Enrich nodes with degree information
all_nodes_enriched = all_nodes.alias("n") \
    .join(
        node_degrees.alias("d"),
        F.col("n.node_id") == F.col("d.source_node_id"),
        "left"
    ) \
    .select(
        "n.*",
        F.coalesce(F.col("d.total_degree"), F.lit(0)).alias("node_degree")
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Gold Layer

# COMMAND ----------

# Load configuration
with open("/dbfs/FileStore/configs/data-sources.yml", "r") as f:
    config = yaml.safe_load(f)

gold_path = config['storage']['gold_path']

# Write nodes
nodes_path = f"{gold_path}/nodes"
nodes_table = f"neo4j_pipeline_{environment}.gold.nodes"

all_nodes_enriched.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .option("path", nodes_path) \
    .saveAsTable(nodes_table)

print(f"✅ Nodes written to: {nodes_table}")

# Write relationships
relationships_path = f"{gold_path}/relationships"
relationships_table = f"neo4j_pipeline_{environment}.gold.relationships"

all_relationships.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .option("path", relationships_path) \
    .saveAsTable(relationships_table)

print(f"✅ Relationships written to: {relationships_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Graph Statistics

# COMMAND ----------

print("\n" + "="*60)
print("GRAPH STATISTICS")
print("="*60)

# Node statistics
node_stats = all_nodes_enriched.groupBy("node_label").agg(
    F.count("*").alias("count"),
    F.avg("node_degree").alias("avg_degree"),
    F.max("node_degree").alias("max_degree")
)

print("\nNode Statistics:")
node_stats.show(truncate=False)

# Relationship statistics
rel_stats = all_relationships.groupBy("relationship_type").agg(
    F.count("*").alias("count")
)

print("\nRelationship Statistics:")
rel_stats.show(truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Checks

# COMMAND ----------

print("\n" + "="*60)
print("DATA QUALITY CHECKS")
print("="*60)

# Check for orphaned nodes (nodes with no relationships)
orphaned_nodes = all_nodes_enriched.filter(F.col("node_degree") == 0)
orphan_count = orphaned_nodes.count()

if orphan_count > 0:
    print(f"\n⚠️  Found {orphan_count} orphaned nodes")
    orphaned_nodes.groupBy("node_label").count().show()
else:
    print("\n✅ No orphaned nodes found")

# Check for invalid relationships (missing source or target nodes)
nodes_ids = all_nodes.select("node_id").distinct()

invalid_sources = all_relationships \
    .join(nodes_ids, all_relationships.source_node_id == nodes_ids.node_id, "left_anti") \
    .count()

invalid_targets = all_relationships \
    .join(nodes_ids, all_relationships.target_node_id == nodes_ids.node_id, "left_anti") \
    .count()

if invalid_sources > 0 or invalid_targets > 0:
    print(f"\n⚠️  Found invalid relationships:")
    print(f"  - Invalid sources: {invalid_sources}")
    print(f"  - Invalid targets: {invalid_targets}")
else:
    print("\n✅ All relationships are valid")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

summary = {
    'nodes_total': all_nodes_enriched.count(),
    'relationships_total': all_relationships.count(),
    'orphaned_nodes': orphan_count,
    'invalid_relationships': invalid_sources + invalid_targets
}

print("\n" + "="*60)
print("TRANSFORMATION SUMMARY")
print("="*60)
print(f"\nTotal Nodes: {summary['nodes_total']}")
print(f"Total Relationships: {summary['relationships_total']}")
print(f"Orphaned Nodes: {summary['orphaned_nodes']}")
print(f"Invalid Relationships: {summary['invalid_relationships']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Exit

# COMMAND ----------

dbutils.notebook.exit(f"SUCCESS: Transformed {summary['nodes_total']} nodes and {summary['relationships_total']} relationships")
