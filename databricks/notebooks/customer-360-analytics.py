# Databricks notebook source
# MAGIC %md
# MAGIC # Customer 360 Analytics
# MAGIC 
# MAGIC Comprehensive customer view combining purchase history, preferences, and behavior patterns.
# MAGIC 
# MAGIC **Features:**
# MAGIC - Complete customer profile
# MAGIC - Purchase history and patterns
# MAGIC - Product preferences
# MAGIC - Customer segmentation
# MAGIC - Lifetime value analysis

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import *
import json

# Get parameters (single environment)
dbutils.widgets.text("customer_id", "", "Customer ID (optional)")
customer_id_filter = dbutils.widgets.get("customer_id")

# Resolve Unity Catalog (prefer 'neo4j_pipeline', else first available)
def _get_catalog_names():
    try:
        df = spark.sql("SHOW CATALOGS")
        return [row.catalog for row in df.collect()]
    except Exception:
        return []

preferred_catalog = "neo4j_pipeline"
catalogs = _get_catalog_names()
catalog = preferred_catalog if preferred_catalog in catalogs else (catalogs[0] if catalogs else preferred_catalog)
print(f"Catalog resolved to: {catalog}")
spark.sql(f"USE CATALOG {catalog}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Customer Profile Enrichment

# COMMAND ----------

# Build comprehensive customer profile
customer_profile = spark.table(f"{catalog}.silver.customers").alias("c") \
    .join(
        spark.table(f"{catalog}.gold.customer_metrics").alias("cm"),
        F.col("c.id") == F.col("cm.customer_id"),
        "left"
    ) \
    .select(
        F.col("c.id").alias("customer_id"),
        F.col("c.name"),
        F.col("c.email"),
        F.col("c.age"),
        F.col("c.gender"),
        F.col("c.city"),
        F.col("c.country"),
        F.col("c.customer_segment"),
        F.col("c.preferences"),
        F.coalesce(F.col("cm.total_orders"), F.lit(0)).alias("total_orders"),
        F.coalesce(F.col("cm.lifetime_value"), F.lit(0.0)).alias("lifetime_value"),
        F.coalesce(F.col("cm.avg_order_value"), F.lit(0.0)).alias("avg_order_value"),
        F.col("cm.last_order_date"),
        F.col("cm.first_order_date"),
        F.coalesce(F.col("cm.days_since_last_order"), F.lit(9999)).alias("days_since_last_order")
    )

# Apply filter if customer ID specified
if customer_id_filter:
    customer_profile = customer_profile.filter(F.col("customer_id") == customer_id_filter)

customer_profile.createOrReplaceTempView("customer_profile")

print(f"✅ Created customer profiles for {customer_profile.count()} customers")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Purchase History Analysis

# COMMAND ----------

# Detailed purchase history
purchase_history = spark.table(f"{catalog}.silver.orders").alias("o") \
    .join(
        spark.table(f"{catalog}.silver.products").alias("p"),
        F.col("o.product_id") == F.col("p.id")
    ) \
    .select(
        F.col("o.customer_id"),
        F.col("o.id").alias("order_id"),
        F.col("o.order_date"),
        F.col("p.name").alias("product_name"),
        F.col("p.category"),
        F.col("p.subcategory"),
        F.col("o.quantity"),
        F.col("o.total_amount"),
        F.col("o.status"),
        F.col("o.payment_method")
    ) \
    .orderBy(F.col("o.order_date").desc())

if customer_id_filter:
    purchase_history = purchase_history.filter(F.col("customer_id") == customer_id_filter)

purchase_history.createOrReplaceTempView("purchase_history")

print(f"✅ Loaded {purchase_history.count()} purchase records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Category Preferences

# COMMAND ----------

# Analyze category preferences by spending
category_preferences = spark.table(f"{catalog}.silver.orders").alias("o") \
    .join(
        spark.table(f"{catalog}.silver.products").alias("p"),
        F.col("o.product_id") == F.col("p.id")
    ) \
    .groupBy(F.col("o.customer_id"), F.col("p.category")) \
    .agg(
        F.count("o.id").alias("purchase_count"),
        F.sum("o.total_amount").alias("total_spent"),
        F.avg("o.total_amount").alias("avg_spent")
    ) \
    .withColumn(
        "rank",
        F.row_number().over(
            Window.partitionBy("customer_id").orderBy(F.col("total_spent").desc())
        )
    ) \
    .filter(F.col("rank") <= 5)  # Top 5 categories per customer

if customer_id_filter:
    category_preferences = category_preferences.filter(F.col("customer_id") == customer_id_filter)

category_preferences.createOrReplaceTempView("category_preferences")

print(f"✅ Analyzed category preferences")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Review Behavior

# COMMAND ----------

# Customer review patterns
review_behavior = spark.table(f"{catalog}.silver.reviews").alias("r") \
    .join(
        spark.table(f"{catalog}.silver.products").alias("p"),
        F.col("r.product_id") == F.col("p.id")
    ) \
    .groupBy(F.col("r.customer_id")) \
    .agg(
        F.count("r.id").alias("total_reviews"),
        F.avg("r.rating").alias("avg_rating_given"),
        F.countDistinct("p.category").alias("categories_reviewed")
    )

if customer_id_filter:
    review_behavior = review_behavior.filter(F.col("customer_id") == customer_id_filter)

review_behavior.createOrReplaceTempView("review_behavior")

print(f"✅ Analyzed review behavior")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Customer 360 View

# COMMAND ----------

# Combine all dimensions into Customer 360
customer_360 = customer_profile.alias("cp") \
    .join(review_behavior.alias("rb"), F.col("cp.customer_id") == F.col("rb.customer_id"), "left") \
    .select(
        F.col("cp.*"),
        F.coalesce(F.col("rb.total_reviews"), F.lit(0)).alias("total_reviews"),
        F.coalesce(F.col("rb.avg_rating_given"), F.lit(0.0)).alias("avg_rating_given"),
        F.coalesce(F.col("rb.categories_reviewed"), F.lit(0)).alias("categories_reviewed")
    )

# Calculate engagement score
customer_360 = customer_360.withColumn(
    "engagement_score",
    (
        (F.col("total_orders") * 0.4) +
        (F.col("total_reviews") * 0.3) +
        (F.when(F.col("days_since_last_order") < 30, 20)
          .when(F.col("days_since_last_order") < 90, 10)
          .otherwise(0) * 0.3)
    )
)

# Classify customer value
customer_360 = customer_360.withColumn(
    "customer_value_tier",
    F.when(F.col("lifetime_value") > 5000, "VIP")
     .when(F.col("lifetime_value") > 2000, "High Value")
     .when(F.col("lifetime_value") > 500, "Medium Value")
     .otherwise("Low Value")
)

# Save Customer 360
customer_360.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.analytics.customer_360")

print(f"✅ Created Customer 360 view for {customer_360.count()} customers")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Top Customers Report

# COMMAND ----------

# Display top customers
top_customers = customer_360 \
    .orderBy(F.col("lifetime_value").desc()) \
    .limit(20) \
    .select(
        "customer_id",
        "name",
        "city",
        "customer_segment",
        "total_orders",
        "lifetime_value",
        "avg_order_value",
        "days_since_last_order",
        "customer_value_tier",
        "engagement_score"
    )

display(top_customers)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Customer Segmentation

# COMMAND ----------

# Create customer segments
customer_segments = customer_360 \
    .withColumn(
        "rfm_segment",
        F.when(
            (F.col("days_since_last_order") < 30) &
            (F.col("total_orders") > 10) &
            (F.col("lifetime_value") > 2000),
            "Champions"
        ).when(
            (F.col("days_since_last_order") < 60) &
            (F.col("total_orders") > 5),
            "Loyal Customers"
        ).when(
            (F.col("days_since_last_order") < 90) &
            (F.col("lifetime_value") > 1000),
            "Potential Loyalists"
        ).when(
            F.col("days_since_last_order") > 180,
            "At Risk"
        ).when(
            F.col("total_orders") == 1,
            "New Customers"
        ).otherwise("Regular Customers")
    )

# Segment summary
segment_summary = customer_segments \
    .groupBy("rfm_segment") \
    .agg(
        F.count("customer_id").alias("customer_count"),
        F.sum("lifetime_value").alias("total_revenue"),
        F.avg("lifetime_value").alias("avg_lifetime_value"),
        F.avg("total_orders").alias("avg_orders")
    ) \
    .orderBy(F.col("total_revenue").desc())

display(segment_summary)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load to Neo4j

# COMMAND ----------

# Prepare customer data for Neo4j with enriched attributes
neo4j_customers = customer_360.select(
    F.col("customer_id").alias("id"),
    F.struct(
        F.col("name"),
        F.col("email"),
        F.col("age"),
        F.col("gender"),
        F.col("city"),
        F.col("country"),
        F.col("customer_segment"),
        F.col("lifetime_value"),
        F.col("total_orders"),
        F.col("avg_order_value"),
        F.col("customer_value_tier"),
        F.col("engagement_score")
    ).alias("properties")
)

# Write to graph_ready table
neo4j_customers.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.graph_ready.customer_360_nodes")

print(f"✅ Prepared {neo4j_customers.count()} enriched customer nodes for Neo4j")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print("Customer 360 Analytics Complete")
print("=" * 60)
print(f"\nCatalog: {catalog}")
print("\nCustomer Insights:")
print(f"  Total Customers: {customer_360.count()}")
print(f"  Active Customers (< 90 days): {customer_360.filter(F.col('days_since_last_order') < 90).count()}")
print(f"  VIP Customers: {customer_360.filter(F.col('customer_value_tier') == 'VIP').count()}")
print("\nSegment Distribution:")
segment_summary.select("rfm_segment", "customer_count").show(truncate=False)
print("✅ Customer 360 analysis complete!")
print("=" * 60)
