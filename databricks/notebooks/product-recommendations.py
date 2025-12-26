# Databricks notebook source
# MAGIC %md
# MAGIC # Product Recommendation Engine
# MAGIC 
# MAGIC Generate product recommendations using collaborative filtering and Neo4j graph algorithms.
# MAGIC 
# MAGIC **Recommendation Strategies:**
# MAGIC 1. Collaborative Filtering (customers who bought X also bought Y)
# MAGIC 2. Content-Based (similar products by category)
# MAGIC 3. Cross-Category Recommendations
# MAGIC 4. Trending Products

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
dbutils.widgets.text("top_n", "10", "Number of recommendations")
customer_id_filter = dbutils.widgets.get("customer_id")
top_n = int(dbutils.widgets.get("top_n"))

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
print(f"Top N Recommendations: {top_n}")
spark.sql(f"USE CATALOG {catalog}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Collaborative Filtering Recommendations

# COMMAND ----------

# Build customer-product purchase matrix
customer_purchases = spark.table(f"{catalog}.silver.orders") \
    .select("customer_id", "product_id") \
    .distinct()

# Find similar customers (customers who bought the same products)
similar_customers = customer_purchases.alias("cp1") \
    .join(
        customer_purchases.alias("cp2"),
        F.col("cp1.product_id") == F.col("cp2.product_id")
    ) \
    .filter(F.col("cp1.customer_id") != F.col("cp2.customer_id")) \
    .groupBy(F.col("cp1.customer_id").alias("customer_id"), 
             F.col("cp2.customer_id").alias("similar_customer_id")) \
    .agg(F.count("cp1.product_id").alias("common_products"))

print(f"✅ Identified similar customer pairs")

# COMMAND ----------

# Generate collaborative filtering recommendations
collaborative_recommendations = similar_customers.alias("sc") \
    .join(
        customer_purchases.alias("cp"),
        F.col("sc.similar_customer_id") == F.col("cp.customer_id")
    ) \
    .join(
        customer_purchases.alias("purchased"),
        (F.col("sc.customer_id") == F.col("purchased.customer_id")) &
        (F.col("cp.product_id") == F.col("purchased.product_id")),
        "left_anti"
    ) \
    .groupBy(F.col("sc.customer_id"), F.col("cp.product_id")) \
    .agg(
        F.sum("sc.common_products").alias("recommendation_score")
    ) \
    .withColumn(
        "rank",
        F.row_number().over(
            Window.partitionBy("customer_id")
            .orderBy(F.col("recommendation_score").desc())
        )
    ) \
    .filter(F.col("rank") <= top_n)

# Enrich with product details
collaborative_recommendations = collaborative_recommendations \
    .join(
        spark.table(f"{catalog}.silver.products"),
        collaborative_recommendations.product_id == F.col("id")
    ) \
    .select(
        F.col("customer_id"),
        F.col("product_id"),
        F.col("name").alias("product_name"),
        F.col("category"),
        F.col("price"),
        F.col("recommendation_score"),
        F.lit("Collaborative Filtering").alias("recommendation_type"),
        F.col("rank")
    )

print(f"✅ Generated collaborative filtering recommendations")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Category-Based Recommendations

# COMMAND ----------
# Find customer's favorite categories
customer_category_prefs = spark.table(f"{catalog}.silver.orders").alias("o") \
    .join(
        spark.table(f"{catalog}.silver.products").alias("p"),
        F.col("o.product_id") == F.col("p.id")
    ) \
    .groupBy(F.col("o.customer_id"), F.col("p.category")) \
    .agg(
        F.count("o.id").alias("purchase_count"),
        F.sum("o.total_amount").alias("total_spent")
    ) \
    .withColumn(
        "category_rank",
        F.row_number().over(
            Window.partitionBy("customer_id")
            .orderBy(F.col("total_spent").desc())
        )
    ) \
    .filter(F.col("category_rank") <= 3)  # Top 3 categories

# Recommend popular products from favorite categories that customer hasn't bought
category_recommendations = customer_category_prefs.alias("ccp") \
    .join(
        spark.table(f"{catalog}.gold.product_metrics").alias("pm"),
        F.col("pm.total_revenue").isNotNull()
    ) \
    .join(
        spark.table(f"{catalog}.silver.products").alias("p"),
        F.col("pm.product_id") == F.col("p.id")
    ) \
    .filter(F.col("ccp.category") == F.col("p.category")) \
    .join(
        customer_purchases.alias("cp"),
        (F.col("ccp.customer_id") == F.col("cp.customer_id")) &
        (F.col("p.id") == F.col("cp.product_id")),
        "left_anti"
    ) \
    .select(
        F.col("ccp.customer_id"),
        F.col("p.id").alias("product_id"),
        F.col("p.name").alias("product_name"),
        F.col("p.category"),
        F.col("p.price"),
        (F.col("pm.total_revenue") * F.col("ccp.category_rank")).alias("recommendation_score"),
        F.lit("Category-Based").alias("recommendation_type")
    ) \
    .withColumn(
        "rank",
        F.row_number().over(
            Window.partitionBy("customer_id")
            .orderBy(F.col("recommendation_score").desc())
        )
    ) \
    .filter(F.col("rank") <= top_n)

print(f"✅ Generated category-based recommendations")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Review-Based Recommendations

# COMMAND ----------

# Recommend highly-rated products from categories customer has purchased
review_based_recommendations = spark.table(f"{catalog}.silver.orders").alias("o") \
    .join(
        spark.table(f"{catalog}.silver.products").alias("p1"),
        F.col("o.product_id") == F.col("p1.id")
    ) \
    .select(F.col("o.customer_id"), F.col("p1.category")) \
    .distinct() \
    .join(
        spark.table(f"{catalog}.gold.product_metrics").alias("pm"),
        (F.col("pm.avg_rating") >= 4.0) &
        (F.col("pm.review_count") >= 5)
    ) \
    .join(
        spark.table(f"{catalog}.silver.products").alias("p2"),
        (F.col("pm.product_id") == F.col("p2.id")) &
        (F.col("category") == F.col("p2.category"))
    ) \
    .join(
        customer_purchases.alias("cp"),
        (F.col("customer_id") == F.col("cp.customer_id")) &
        (F.col("p2.id") == F.col("cp.product_id")),
        "left_anti"
    ) \
    .select(
        F.col("customer_id"),
        F.col("p2.id").alias("product_id"),
        F.col("p2.name").alias("product_name"),
        F.col("p2.category"),
        F.col("p2.price"),
        (F.col("pm.avg_rating") * F.col("pm.review_count")).alias("recommendation_score"),
        F.lit("High-Rated").alias("recommendation_type")
    ) \
    .withColumn(
        "rank",
        F.row_number().over(
            Window.partitionBy("customer_id")
            .orderBy(F.col("recommendation_score").desc())
        )
    ) \
    .filter(F.col("rank") <= top_n)

print(f"✅ Generated review-based recommendations")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Trending Products

# COMMAND ----------

# Identify trending products (high recent sales velocity)
recent_date = spark.table(f"{catalog}.silver.orders").agg(F.max("order_date")).collect()[0][0]
days_back = 30

trending_products = spark.table(f"{catalog}.silver.orders") \
    .filter(F.datediff(F.lit(recent_date), F.col("order_date")) <= days_back) \
    .groupBy("product_id") \
    .agg(
        F.count("id").alias("recent_orders"),
        F.sum("total_amount").alias("recent_revenue")
    ) \
    .join(
        spark.table(f"{catalog}.silver.products"),
        F.col("product_id") == F.col("id")
    ) \
    .select(
        F.col("id").alias("product_id"),
        F.col("name").alias("product_name"),
        F.col("category"),
        F.col("price"),
        F.col("recent_orders"),
        F.col("recent_revenue")
    ) \
    .orderBy(F.col("recent_orders").desc()) \
    .limit(50)

print(f"✅ Identified {trending_products.count()} trending products")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Combined Recommendations

# COMMAND ----------

# Combine all recommendation types
all_recommendations = collaborative_recommendations \
    .union(category_recommendations) \
    .union(review_based_recommendations)

# Deduplicate and re-rank
final_recommendations = all_recommendations \
    .groupBy("customer_id", "product_id", "product_name", "category", "price") \
    .agg(
        F.sum("recommendation_score").alias("total_score"),
        F.collect_set("recommendation_type").alias("recommendation_sources")
    ) \
    .withColumn(
        "final_rank",
        F.row_number().over(
            Window.partitionBy("customer_id")
            .orderBy(F.col("total_score").desc())
        )
    ) \
    .filter(F.col("final_rank") <= top_n)

# Save recommendations
final_recommendations.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.analytics.product_recommendations")

print(f"✅ Generated final recommendations for {final_recommendations.select('customer_id').distinct().count()} customers")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample Customer Recommendations

# COMMAND ----------

if customer_id_filter:
    customer_recs = final_recommendations.filter(F.col("customer_id") == customer_id_filter)
else:
    # Show recommendations for a sample customer
    sample_customer = final_recommendations.select("customer_id").limit(1).collect()[0][0]
    customer_recs = final_recommendations.filter(F.col("customer_id") == sample_customer)

print(f"Recommendations for Customer {customer_recs.select('customer_id').first()[0]}:")
display(customer_recs.select(
    "final_rank",
    "product_name",
    "category",
    "price",
    "total_score",
    "recommendation_sources"
).orderBy("final_rank"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Neo4j RECOMMENDS Relationships

# COMMAND ----------

# Prepare recommendation relationships for Neo4j
neo4j_recommendations = final_recommendations \
    .select(
        F.col("customer_id").alias("from_id"),
        F.col("product_id").alias("to_id"),
        F.struct(
            F.col("total_score").alias("score"),
            F.col("recommendation_sources").alias("algorithms"),
            F.col("final_rank").alias("rank")
        ).alias("properties")
    ) \
    .withColumn("rel_type", F.lit("RECOMMENDS"))

# Save to graph_ready
neo4j_recommendations.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.graph_ready.recommends_relationships")

print(f"✅ Created {neo4j_recommendations.count()} RECOMMENDS relationships for Neo4j")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Recommendation Statistics

# COMMAND ----------

# Calculate recommendation coverage
total_customers = spark.table(f"{catalog}.silver.customers").count()
customers_with_recs = final_recommendations.select("customer_id").distinct().count()
coverage_pct = (customers_with_recs / total_customers) * 100

print("=" * 60)
print("Product Recommendation Engine Summary")
print("=" * 60)
print(f"Catalog: {catalog}")
print("\nRecommendation Coverage:")
print(f"  Total Customers: {total_customers}")
print(f"  Customers with Recommendations: {customers_with_recs}")
print(f"  Coverage: {coverage_pct:.1f}%")
print("\nRecommendation Distribution:")

# Show distribution by recommendation type
rec_type_dist = all_recommendations \
    .groupBy("recommendation_type") \
    .agg(
        F.countDistinct("customer_id").alias("customers"),
        F.count("product_id").alias("recommendations")
    ) \
    .show()

print("\nTrending Products (Top 10):")
trending_products.select("product_name", "category", "recent_orders", "recent_revenue") \
    .show(10, truncate=False)

print("\n✅ Recommendation engine complete!")
print("=" * 60)
