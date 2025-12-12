# Databricks notebook source
# MAGIC %md
# MAGIC # E-commerce Data ETL Pipeline
# MAGIC 
# MAGIC Complete ETL pipeline for e-commerce data from CSV to Neo4j-ready format.
# MAGIC 
# MAGIC **Pipeline Stages:**
# MAGIC 1. Bronze: Raw data ingestion from CSV
# MAGIC 2. Silver: Data cleaning and validation
# MAGIC 3. Gold: Business-level aggregations
# MAGIC 4. Graph Ready: Neo4j formatted data
# MAGIC 
# MAGIC **Parameters:**
# MAGIC - `environment`: Target environment (dev/staging/prod)
# MAGIC - `catalog`: Unity Catalog name

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup and Configuration

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.window import Window
from datetime import datetime
import yaml

# Get parameters
dbutils.widgets.text("environment", "dev", "Environment")
dbutils.widgets.text("catalog", "ecommerce_dev", "Unity Catalog")

environment = dbutils.widgets.get("environment")
catalog = dbutils.widgets.get("catalog")

print(f"Environment: {environment}")
print(f"Catalog: {catalog}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Layer - Raw Data Ingestion

# COMMAND ----------

# Read customers
customers_raw = spark.read.format("csv") \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .load("/mnt/ecommerce-data/sample-data/customers.csv")

# Write to bronze
customers_raw.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.bronze.customers_raw")

print(f"✅ Loaded {customers_raw.count()} customers to bronze layer")

# COMMAND ----------

# Read products
products_raw = spark.read.format("csv") \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .load("/mnt/ecommerce-data/sample-data/products.csv")

products_raw.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.bronze.products_raw")

print(f"✅ Loaded {products_raw.count()} products to bronze layer")

# COMMAND ----------

# Read orders
orders_raw = spark.read.format("csv") \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .load("/mnt/ecommerce-data/sample-data/orders.csv")

orders_raw.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.bronze.orders_raw")

print(f"✅ Loaded {orders_raw.count()} orders to bronze layer")

# COMMAND ----------

# Read reviews
reviews_raw = spark.read.format("csv") \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .load("/mnt/ecommerce-data/sample-data/reviews.csv")

reviews_raw.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.bronze.reviews_raw")

print(f"✅ Loaded {reviews_raw.count()} reviews to bronze layer")

# COMMAND ----------

# Read suppliers
suppliers_raw = spark.read.format("csv") \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .load("/mnt/ecommerce-data/sample-data/suppliers.csv")

suppliers_raw.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.bronze.suppliers_raw")

print(f"✅ Loaded {suppliers_raw.count()} suppliers to bronze layer")

# COMMAND ----------

# Read categories
categories_raw = spark.read.format("csv") \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .load("/mnt/ecommerce-data/sample-data/categories.csv")

categories_raw.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.bronze.categories_raw")

print(f"✅ Loaded {categories_raw.count()} categories to bronze layer")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Layer - Data Cleaning and Validation

# COMMAND ----------

# Clean customers data
customers_silver = spark.table(f"{catalog}.bronze.customers_raw") \
    .dropDuplicates(["id"]) \
    .filter(F.col("email").isNotNull()) \
    .filter(F.col("email").rlike("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$")) \
    .withColumn("age_group", 
                F.when(F.col("age") < 25, "18-24")
                 .when(F.col("age") < 35, "25-34")
                 .when(F.col("age") < 45, "35-44")
                 .when(F.col("age") < 55, "45-54")
                 .when(F.col("age") < 65, "55-64")
                 .otherwise("65+")) \
    .withColumn("processing_timestamp", F.current_timestamp())

customers_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.silver.customers")

print(f"✅ Cleaned {customers_silver.count()} customers to silver layer")

# COMMAND ----------

# Clean products data
products_silver = spark.table(f"{catalog}.bronze.products_raw") \
    .dropDuplicates(["id"]) \
    .filter(F.col("price") > 0) \
    .withColumn("price_tier",
                F.when(F.col("price") < 50, "Budget")
                 .when(F.col("price") < 200, "Mid-range")
                 .when(F.col("price") < 500, "Premium")
                 .otherwise("Luxury")) \
    .withColumn("in_stock", F.col("stock_quantity") > 0) \
    .withColumn("processing_timestamp", F.current_timestamp())

products_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.silver.products")

print(f"✅ Cleaned {products_silver.count()} products to silver layer")

# COMMAND ----------

# Clean orders data
orders_silver = spark.table(f"{catalog}.bronze.orders_raw") \
    .dropDuplicates(["id"]) \
    .filter(F.col("total_amount") > 0) \
    .filter(F.col("status").isin(["completed", "shipped", "processing", "cancelled"])) \
    .withColumn("order_year", F.year(F.col("order_date"))) \
    .withColumn("order_month", F.month(F.col("order_date"))) \
    .withColumn("order_quarter", F.quarter(F.col("order_date"))) \
    .withColumn("processing_timestamp", F.current_timestamp())

orders_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.silver.orders")

print(f"✅ Cleaned {orders_silver.count()} orders to silver layer")

# COMMAND ----------

# Clean reviews data
reviews_silver = spark.table(f"{catalog}.bronze.reviews_raw") \
    .dropDuplicates(["id"]) \
    .filter(F.col("rating").between(1, 5)) \
    .withColumn("sentiment",
                F.when(F.col("rating") >= 4, "Positive")
                 .when(F.col("rating") == 3, "Neutral")
                 .otherwise("Negative")) \
    .withColumn("processing_timestamp", F.current_timestamp())

reviews_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.silver.reviews")

print(f"✅ Cleaned {reviews_silver.count()} reviews to silver layer")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Layer - Business Aggregations

# COMMAND ----------

# Customer metrics
customer_metrics = spark.table(f"{catalog}.silver.orders") \
    .groupBy("customer_id") \
    .agg(
        F.count("id").alias("total_orders"),
        F.sum("total_amount").alias("lifetime_value"),
        F.avg("total_amount").alias("avg_order_value"),
        F.max("order_date").alias("last_order_date"),
        F.min("order_date").alias("first_order_date")
    ) \
    .withColumn("days_since_last_order",
                F.datediff(F.current_date(), F.col("last_order_date"))) \
    .withColumn("customer_tenure_days",
                F.datediff(F.col("last_order_date"), F.col("first_order_date")))

customer_metrics.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.gold.customer_metrics")

print(f"✅ Created customer metrics for {customer_metrics.count()} customers")

# COMMAND ----------

# Product metrics
product_metrics = spark.table(f"{catalog}.silver.orders") \
    .groupBy("product_id") \
    .agg(
        F.count("id").alias("total_orders"),
        F.sum("quantity").alias("total_quantity_sold"),
        F.sum("total_amount").alias("total_revenue")
    ) \
    .join(
        spark.table(f"{catalog}.silver.reviews")
            .groupBy("product_id")
            .agg(
                F.count("id").alias("review_count"),
                F.avg("rating").alias("avg_rating")
            ),
        "product_id",
        "left"
    )

product_metrics.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.gold.product_metrics")

print(f"✅ Created product metrics for {product_metrics.count()} products")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Graph Ready Layer - Neo4j Format

# COMMAND ----------

# Customer nodes
customer_nodes = spark.table(f"{catalog}.silver.customers") \
    .select(
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
    ) \
    .withColumn("label", F.lit("Customer"))

customer_nodes.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.graph_ready.customer_nodes")

print(f"✅ Created {customer_nodes.count()} customer nodes")

# COMMAND ----------

# Product nodes
product_nodes = spark.table(f"{catalog}.silver.products") \
    .select(
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
    ) \
    .withColumn("label", F.lit("Product"))

product_nodes.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.graph_ready.product_nodes")

print(f"✅ Created {product_nodes.count()} product nodes")

# COMMAND ----------

# PURCHASED relationships
purchased_rels = spark.table(f"{catalog}.silver.orders") \
    .select(
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
    ) \
    .withColumn("rel_type", F.lit("PURCHASED"))

purchased_rels.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.graph_ready.purchased_relationships")

print(f"✅ Created {purchased_rels.count()} PURCHASED relationships")

# COMMAND ----------

# REVIEWED relationships
reviewed_rels = spark.table(f"{catalog}.silver.reviews") \
    .select(
        F.col("customer_id").alias("from_id"),
        F.col("product_id").alias("to_id"),
        F.to_json(F.struct(
            F.col("rating"),
            F.col("review_text"),
            F.col("review_date"),
            F.col("sentiment")
        )).alias("properties")
    ) \
    .withColumn("rel_type", F.lit("REVIEWED"))

reviewed_rels.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(f"{catalog}.graph_ready.reviewed_relationships")

print(f"✅ Created {reviewed_rels.count()} REVIEWED relationships")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Summary

# COMMAND ----------

print("=" * 60)
print("E-commerce ETL Pipeline Complete")
print("=" * 60)
print(f"\nEnvironment: {environment}")
print(f"Catalog: {catalog}")
print("\nData Processed:")
print(f"  Customers: {customers_silver.count()}")
print(f"  Products: {products_silver.count()}")
print(f"  Orders: {orders_silver.count()}")
print(f"  Reviews: {reviews_silver.count()}")
print(f"  Suppliers: {suppliers_raw.count()}")
print(f"  Categories: {categories_raw.count()}")
print("\nGraph Ready:")
print(f"  Customer Nodes: {customer_nodes.count()}")
print(f"  Product Nodes: {product_nodes.count()}")
print(f"  PURCHASED Relationships: {purchased_rels.count()}")
print(f"  REVIEWED Relationships: {reviewed_rels.count()}")
print("\n✅ Pipeline execution successful!")
print("=" * 60)
