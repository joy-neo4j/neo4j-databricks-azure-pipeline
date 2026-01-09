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

# Helpers
def table_exists(fullname: str) -> bool:
    try:
        spark.table(fullname)
        return True
    except Exception:
        return False

def has_columns(df, cols):
    s = set(c.lower() for c in df.columns)
    return all(c.lower() in s for c in cols)

map_str_str = T.MapType(T.StringType(), T.StringType())

def merge_props_json(props_col, add_map_col):
    """Merge a JSON string column with a map<string,string> column to a new JSON string."""
    return F.to_json(F.map_concat(F.coalesce(F.from_json(props_col, map_str_str), F.create_map()), add_map_col))

# COMMAND ----------
# 1) Product category enrichment
prod_nodes_tbl = f"{CATALOG}.graph_ready.product_nodes"
prod_silver_tbl = f"{CATALOG}.silver.products"
if table_exists(prod_nodes_tbl) and table_exists(prod_silver_tbl):
    prod_nodes = spark.table(prod_nodes_tbl).select("node_id", "properties")
    prod_silver = spark.table(prod_silver_tbl)
    # Determine a category column if present
    category_col = None
    for cand in ["category", "category_name", "category_id"]:
        if cand in [c.lower() for c in prod_silver.columns]:
            # preserve original case
            for real in prod_silver.columns:
                if real.lower() == cand:
                    category_col = real
                    break
            if category_col:
                break
    if category_col is not None:
        enriched = prod_nodes.alias("n").join(
            prod_silver.select(F.col("product_id").cast("string").alias("node_id"), F.col(category_col).cast("string").alias("category")),
            on="node_id", how="left"
        ).withColumn(
            "properties",
            merge_props_json(F.col("properties"), F.map_from_arrays(F.array(F.lit("category")), F.array(F.col("category"))))
        ).select("node_id", "properties")
        enriched.write.mode("overwrite").saveAsTable(prod_nodes_tbl)
        print("✓ Enriched product_nodes with category")
    else:
        print("(skip) No category-like column found in silver.products")
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
    date_col = next((c for c in ["purchase_date","order_date","created_at","timestamp","date"] if c in [x.lower() for x in orders.columns]), None)
    amt_col  = next((c for c in ["amount","price","total_amount","unit_price","subtotal"] if c in [x.lower() for x in orders.columns]), None)
    cust_col = next((c for c in ["customer_id","user_id"] if c in [x.lower() for x in orders.columns]), None)
    prod_col = next((c for c in ["product_id","sku","item_id"] if c in [x.lower() for x in orders.columns]), None)

    if date_col and cust_col and prod_col:
        # Recover real-case columns
        def real(colname):
            for rc in orders.columns:
                if rc.lower() == colname:
                    return rc
            return colname
        date_rc = real(date_col); cust_rc = real(cust_col); prod_rc = real(prod_col)
        amt_rc  = real(amt_col) if amt_col else None

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
    date_col = next((c for c in ["review_date","created_at","timestamp","date"] if c in [x.lower() for x in rev.columns]), None)
    rating_col = next((c for c in ["rating","score","stars"] if c in [x.lower() for x in rev.columns]), None)
    cust_col = next((c for c in ["customer_id","user_id"] if c in [x.lower() for x in rev.columns]), None)
    prod_col = next((c for c in ["product_id","sku","item_id"] if c in [x.lower() for x in rev.columns]), None)

    if date_col and cust_col and prod_col:
        def real(colname):
            for rc in rev.columns:
                if rc.lower() == colname:
                    return rc
            return colname
        date_rc = real(date_col); cust_rc = real(cust_col); prod_rc = real(prod_col)
        rating_rc = real(rating_col) if rating_col else None

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

# Supplier nodes
if table_exists(sup_silver_tbl):
    sup = spark.table(sup_silver_tbl)
    # Pick common columns if present
    sid = next((c for c in ["supplier_id","id"] if c in [x.lower() for x in sup.columns]), None)
    name = next((c for c in ["name","supplier_name"] if c in [x.lower() for x in sup.columns]), None)
    country = next((c for c in ["country","region"] if c in [x.lower() for x in sup.columns]), None)
    def real(df, colname):
        for rc in df.columns:
            if rc.lower() == colname:
                return rc
        return colname
    if sid:
        sid_rc = real(sup, sid)
        sel = sup.select(F.col(sid_rc).cast("string").alias("node_id"))
        props_keys = []
        props_vals = []
        if name:
            name_rc = real(sup, name)
            props_keys.append(F.lit("name")); props_vals.append(F.col(name_rc).cast("string"))
        if country:
            country_rc = real(sup, country)
            props_keys.append(F.lit("country")); props_vals.append(F.col(country_rc).cast("string"))
        if props_keys:
            props_map = F.map_from_arrays(F.array(*props_keys), F.array(*props_vals))
        else:
            props_map = F.create_map()
        sup_nodes = sel.withColumn("properties", F.to_json(props_map))
        sup_nodes.write.mode("overwrite").saveAsTable(f"{CATALOG}.graph_ready.supplier_nodes")
        print("✓ Created graph_ready.supplier_nodes")
    else:
        print("(skip) suppliers table lacks supplier_id or id")
else:
    print("(skip) silver.suppliers missing")

# SUPPLIES relationships (supplier -> product)
if table_exists(prod_silver_tbl):
    prod = spark.table(prod_silver_tbl)
    sid = next((c for c in ["supplier_id","supplier"] if c in [x.lower() for x in prod.columns]), None)
    pid = next((c for c in ["product_id","id","sku","item_id"] if c in [x.lower() for x in prod.columns]), None)
    if sid and pid:
        def real(df, colname):
            for rc in df.columns:
                if rc.lower() == colname:
                    return rc
            return colname
        sid_rc = real(prod, sid)
        pid_rc = real(prod, pid)
        supplies = prod.select(
            F.col(sid_rc).cast("string").alias("from_id"),
            F.col(pid_rc).cast("string").alias("to_id"),
            F.to_json(F.create_map()).alias("properties")
        ).where(F.col("from_id").isNotNull() & F.col("to_id").isNotNull()).dropDuplicates(["from_id","to_id"])
        supplies.write.mode("overwrite").saveAsTable(f"{CATALOG}.graph_ready.supplies_relationships")
        print("✓ Created graph_ready.supplies_relationships")
    else:
        print("(skip) products lacks supplier_id and/or product_id-like field")
else:
    print("(skip) silver.products missing")

print("\n✔ Graph Ready Enhancements completed")
