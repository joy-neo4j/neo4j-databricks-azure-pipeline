# Databricks notebook source
# MAGIC %md
# MAGIC # Graph Ready Enhancements (Optional Enrichment)
# MAGIC
# MAGIC Extends existing graph_ready tables with optional fields if source columns exist, and
# MAGIC creates Supplier graph_ready artifacts when silver data is available.
# MAGIC
# MAGIC Parameters:
# MAGIC - catalog: Unity Catalog name (optional)

# COMMAND ----------

from pyspark.sql import functions as F, types as T

# Parameters
dbutils.widgets.text("catalog", "", "Unity Catalog name")
CATALOG = dbutils.widgets.get("catalog") or "neo4j_pipeline"
print(f"Using catalog: {CATALOG}")

# Type definitions
STRING_MAP_TYPE = T.MapType(T.StringType(), T.StringType())

# Column name candidates for schema-aware lookups
CATEGORY_COLUMNS = ["category", "category_name", "category_id"]
DATE_COLUMNS = ["purchase_date", "order_date", "created_at", "timestamp", "date"]
AMOUNT_COLUMNS = ["amount", "price", "total_amount", "unit_price", "subtotal"]
REVIEW_DATE_COLUMNS = ["review_date", "created_at", "timestamp", "date"]
RATING_COLUMNS = ["rating", "score", "stars"]
CUSTOMER_COLUMNS = ["customer_id", "user_id"]
PRODUCT_COLUMNS = ["product_id", "sku", "item_id"]
SUPPLIER_ID_COLUMNS = ["supplier_id", "id"]
SUPPLIER_NAME_COLUMNS = ["name", "supplier_name"]
SUPPLIER_COUNTRY_COLUMNS = ["country", "region"]
SUPPLIER_COLUMNS_IN_PRODUCTS = ["supplier_id", "supplier"]

# Helpers
def table_exists(fullname: str) -> bool:
    try:
        spark.table(fullname)
        return True
    except Exception:
        return False

def find_real_column(df, desired_lower: str):
    for rc in df.columns:
        if rc.lower() == desired_lower:
            return rc
    return None

# Candidate columns
CATEGORY_COLUMNS = ["category", "category_name", "category_id"]
PRODUCT_ID_COLUMNS = ["product_id", "id", "sku", "item_id"]

map_str_str = T.MapType(T.StringType(), T.StringType())

def merge_props_json(props_col, add_map_col):
    """
    Merge an existing JSON map (string) with an additional map<string,string>, ensuring unique keys.
    New values (add_map_col) take precedence when the same key exists.
    """
    existing = F.coalesce(F.from_json(props_col, map_str_str), F.create_map())
    merged = F.map_zip_with(existing, add_map_col, lambda k, v1, v2: F.coalesce(v2, v1))
    return F.to_json(merged)


# COMMAND ----------

# 1) Product category enrichment
prod_nodes_tbl = f"{CATALOG}.graph_ready.product_nodes"
prod_silver_tbl = f"{CATALOG}.silver.products"

if table_exists(prod_nodes_tbl) and table_exists(prod_silver_tbl):
    prod_nodes = spark.table(prod_nodes_tbl).select("node_id", "properties")
    prod_silver = spark.table(prod_silver_tbl)

    # Detect product id column
    pid_col = None
    for cand in PRODUCT_ID_COLUMNS:
        if cand in [c.lower() for c in prod_silver.columns]:
            pid_col = find_real_column(prod_silver, cand)
            break

    # Detect category column
    category_col = None
    for cand in CATEGORY_COLUMNS:
        if cand in [c.lower() for c in prod_silver.columns]:
            category_col = find_real_column(prod_silver, cand)
            break

    if pid_col is not None and category_col is not None:
        # Step 1: Prepare join DataFrame
        join_df = prod_silver.select(
            F.col(pid_col).cast("string").alias("node_id"),
            F.col(category_col).cast("string").alias("category")
        )

        # Step 2: Join
        enriched = prod_nodes.alias("n").join(join_df, on="node_id", how="left")

        # Step 3: Merge properties (no duplicate keys)
        enriched = enriched.withColumn(
            "properties",
            merge_props_json(
                F.col("properties"),
                F.map_from_arrays(
                    F.array(F.lit("category")),
                    F.array(F.col("category"))
                )
            )
        ).select("node_id", "properties")

        # Step 4: Write result
        enriched.write.mode("overwrite").saveAsTable(prod_nodes_tbl)
        print("✓ Enriched product_nodes with category")
    else:
        print("(skip) Missing product id or category column in silver.products")
else:
    print("(skip) product_nodes or silver.products missing")

# COMMAND ----------

# 2) PURCHASED enrichment: purchase_date and amount
purch_tbl = f"{CATALOG}.graph_ready.purchased_relationships"
orders_tbl = f"{CATALOG}.silver.orders"
if table_exists(purch_tbl) and table_exists(orders_tbl):
    purch = spark.table(purch_tbl).select("from_id", "to_id", "properties")
    orders = spark.table(orders_tbl)
    # Identify columns
    date_col = next((c for c in DATE_COLUMNS if c in [x.lower() for x in orders.columns]), None)
    amt_col  = next((c for c in AMOUNT_COLUMNS if c in [x.lower() for x in orders.columns]), None)
    cust_col = next((c for c in CUSTOMER_COLUMNS if c in [x.lower() for x in orders.columns]), None)
    prod_col = next((c for c in PRODUCT_COLUMNS if c in [x.lower() for x in orders.columns]), None)

    if date_col and cust_col and prod_col:
        # Recover real-case columns
        date_rc = find_real_column(orders, date_col)
        cust_rc = find_real_column(orders, cust_col)
        prod_rc = find_real_column(orders, prod_col)
        amt_rc  = find_real_column(orders, amt_col) if amt_col else None

        o_sel = orders.select(
            F.col(cust_rc).cast("string").alias("from_id"),
            F.col(prod_rc).cast("string").alias("to_id"),
            F.col(date_rc).cast("string").alias("purchase_date"),
            *( [F.col(amt_rc).cast("string").alias("amount")] if amt_rc else [] )
        ).dropDuplicates(["from_id","to_id","purchase_date"])  # simple dedupe

        enriched = purch.alias("p").join(o_sel, on=["from_id","to_id"], how="left")
        add_map = F.map_from_arrays(
            F.array(*([F.lit("purchase_date")] + ([F.lit("amount")] if amt_rc else []))),
            F.array(*([F.col("purchase_date")] + ([F.col("amount")] if amt_rc else [])))
        )
        enriched = enriched.withColumn("properties", merge_props_json(F.col("properties"), add_map)).select("from_id","to_id","properties")
        enriched.write.mode("overwrite").saveAsTable(purch_tbl)
        print("✓ Enriched purchased_relationships with purchase_date" + (" and amount" if amt_rc else ""))
    else:
        print("(skip) Required join columns not found on silver.orders")
else:
    print("(skip) purchased_relationships or silver.orders missing")

# COMMAND ----------

# 3) REVIEWED enrichment: review_date and rating
review_tbl = f"{CATALOG}.graph_ready.reviewed_relationships"
reviews_tbl = f"{CATALOG}.silver.reviews"
if table_exists(review_tbl) and table_exists(reviews_tbl):
    rel = spark.table(review_tbl).select("from_id","to_id","properties")
    rev = spark.table(reviews_tbl)
    date_col = next((c for c in REVIEW_DATE_COLUMNS if c in [x.lower() for x in rev.columns]), None)
    rating_col = next((c for c in RATING_COLUMNS if c in [x.lower() for x in rev.columns]), None)
    cust_col = next((c for c in CUSTOMER_COLUMNS if c in [x.lower() for x in rev.columns]), None)
    prod_col = next((c for c in PRODUCT_COLUMNS if c in [x.lower() for x in rev.columns]), None)

    if date_col and cust_col and prod_col:
        date_rc = find_real_column(rev, date_col)
        cust_rc = find_real_column(rev, cust_col)
        prod_rc = find_real_column(rev, prod_col)
        rating_rc = find_real_column(rev, rating_col) if rating_col else None

        r_sel = rev.select(
            F.col(cust_rc).cast("string").alias("from_id"),
            F.col(prod_rc).cast("string").alias("to_id"),
            F.col(date_rc).cast("string").alias("review_date"),
            *( [F.col(rating_rc).cast("string").alias("rating")] if rating_rc else [] )
        ).dropDuplicates(["from_id","to_id","review_date"])  # simple dedupe

        enriched = rel.alias("r").join(r_sel, on=["from_id","to_id"], how="left")
        add_map = F.map_from_arrays(
            F.array(*([F.lit("review_date")] + ([F.lit("rating")] if rating_rc else []))),
            F.array(*([F.col("review_date")] + ([F.col("rating")] if rating_rc else [])))
        )
        enriched = enriched.withColumn("properties", merge_props_json(F.col("properties"), add_map)).select("from_id","to_id","properties")
        enriched.write.mode("overwrite").saveAsTable(review_tbl)
        print("✓ Enriched reviewed_relationships with review_date" + (" and rating" if rating_rc else ""))
    else:
        print("(skip) Required join columns not found on silver.reviews")
else:
    print("(skip) reviewed_relationships or silver.reviews missing")

# COMMAND ----------

# 4) Supplier graph_ready artifacts (optional)
sup_silver_tbl = f"{CATALOG}.silver.suppliers"
prod_silver_tbl = f"{CATALOG}.silver.products"

# Define candidates (ensure these exist earlier in the notebook)
SUPPLIER_ID_COLUMNS = ["supplier_id", "id"]
SUPPLIER_NAME_COLUMNS = ["name", "supplier_name"]
SUPPLIER_COUNTRY_COLUMNS = ["country", "region"]
SUPPLIER_COLUMNS_IN_PRODUCTS = ["supplier_id", "supplier"]
PRODUCT_COLUMNS = ["product_id", "sku", "item_id"]

# Supplier nodes
if table_exists(sup_silver_tbl):
    sup = spark.table(sup_silver_tbl)

    sid = next((c for c in SUPPLIER_ID_COLUMNS if c in [x.lower() for x in sup.columns]), None)
    name = next((c for c in SUPPLIER_NAME_COLUMNS if c in [x.lower() for x in sup.columns]), None)
    country = next((c for c in SUPPLIER_COUNTRY_COLUMNS if c in [x.lower() for x in sup.columns]), None)

    if sid:
        sid_rc = find_real_column(sup, sid)

        # Build key/value pairs only for present columns
        pairs = []
        if name:
            name_rc = find_real_column(sup, name)
            pairs.extend([F.lit("name"), F.col(name_rc).cast("string")])
        if country:
            country_rc = find_real_column(sup, country)
            pairs.extend([F.lit("country"), F.col(country_rc).cast("string")])

        props_map = F.create_map(*pairs) if pairs else F.create_map()
        # Remove null-valued entries if any
        props_map = F.map_filter(props_map, lambda k, v: v.isNotNull())

        sup_nodes = (
            sup.select(
                F.col(sid_rc).cast("string").alias("node_id"),
                F.to_json(props_map).alias("properties")
            )
            .where(F.col("node_id").isNotNull())
            .dropDuplicates(["node_id"])
        )

        sup_nodes.write.mode("overwrite").saveAsTable(f"{CATALOG}.graph_ready.supplier_nodes")
        print("✓ Created graph_ready.supplier_nodes")
    else:
        print("(skip) suppliers table lacks supplier_id or id")
else:
    print("(skip) silver.suppliers missing")

# SUPPLIES relationships (supplier -> product)
if table_exists(prod_silver_tbl):
    prod = spark.table(prod_silver_tbl)
    sid = next((c for c in SUPPLIER_COLUMNS_IN_PRODUCTS if c in [x.lower() for x in prod.columns]), None)
    pid = next((c for c in (["id"] + PRODUCT_COLUMNS) if c in [x.lower() for x in prod.columns]), None)

    if sid and pid:
        sid_rc = find_real_column(prod, sid)
        pid_rc = find_real_column(prod, pid)
        supplies = (
            prod.select(
                F.col(sid_rc).cast("string").alias("from_id"),
                F.col(pid_rc).cast("string").alias("to_id"),
                F.to_json(F.create_map()).alias("properties")
            )
            .where(F.col("from_id").isNotNull() & F.col("to_id").isNotNull())
            .dropDuplicates(["from_id", "to_id"])
        )
        supplies.write.mode("overwrite").saveAsTable(f"{CATALOG}.graph_ready.supplies_relationships")
        print("✓ Created graph_ready.supplies_relationships")
    else:
        print("(skip) products lacks supplier_id and/or product_id-like field")
else:
    print("(skip) silver.products missing")

print("\n✔ Graph Ready Enhancements completed")