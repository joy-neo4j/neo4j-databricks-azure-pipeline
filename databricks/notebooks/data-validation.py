# Databricks notebook source
# MAGIC %md
# MAGIC # Data Validation and Promotion to Silver
# MAGIC 
# MAGIC Validates Bronze tables and promotes cleaned data to Silver layer.
# MAGIC 
# MAGIC Parameters:
# MAGIC - `catalog`: Unity Catalog name (optional; defaults to neo4j_pipeline or first available)
# MAGIC 
# MAGIC Quality Checks:
# MAGIC - Schema validation, null checks, uniqueness
# MAGIC - Foreign keys (best-effort)
# MAGIC - Basic business rule checks
# MAGIC 
# MAGIC Silver outputs:
# MAGIC - {catalog}.silver.customers
# MAGIC - {catalog}.silver.products
# MAGIC - {catalog}.silver.orders
# MAGIC - {catalog}.silver.reviews

# COMMAND ----------

# MAGIC %pip install pyyaml

# COMMAND ----------

import yaml
from pyspark.sql import functions as F
from pyspark.sql.types import *
from datetime import datetime
from pyspark.sql import SparkSession

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

# COMMAND ----------

# Load configuration
with open("/dbfs/FileStore/configs/data-sources.yml", "r") as f:
    config = yaml.safe_load(f)

sources = config.get('sources', [])
dq_config = config.get('data_quality', {})

print(f"Validating {len(sources)} source(s)")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.silver")

# COMMAND ----------
# Validation helpers
def validate_required_columns(df, source_name, required_columns):
    """Validate that required columns have no null values."""
    issues = []
    
    for col in required_columns:
        if col not in df.columns:
            issues.append({
                'source': source_name,
                'check': 'required_column',
                'column': col,
                'issue': 'Column missing',
                'severity': 'critical'
            })
            continue
        
        null_count = df.filter(F.col(col).isNull()).count()
        if null_count > 0:
            issues.append({
                'source': source_name,
                'check': 'null_values',
                'column': col,
                'issue': f'{null_count} null values found',
                'severity': 'high'
            })
    
    return issues

def validate_unique_columns(df, source_name, unique_columns):
    """Validate uniqueness constraints."""
    issues = []
    
    for col in unique_columns:
        if col not in df.columns:
            continue
        
        total_count = df.count()
        distinct_count = df.select(col).distinct().count()
        
        if total_count != distinct_count:
            duplicate_count = total_count - distinct_count
            issues.append({
                'source': source_name,
                'check': 'uniqueness',
                'column': col,
                'issue': f'{duplicate_count} duplicate values found',
                'severity': 'high'
            })
    
    return issues

def validate_foreign_keys(df, source_name, fk_config):
    """Validate foreign key relationships."""
    issues = []
    
    for fk in fk_config:
        fk_column = fk['column']
        ref_table, ref_column = fk['references'].split('.')
        ref_table_full = f"{CATALOG}.bronze.{ref_table}"
        
        try:
            ref_df = spark.table(ref_table_full)
            
            # Get foreign key values not in reference table
            invalid_fks = df.select(fk_column) \
                .distinct() \
                .join(
                    ref_df.select(F.col(ref_column).alias('ref_val')),
                    df[fk_column] == F.col('ref_val'),
                    'left_anti'
                ) \
                .filter(F.col(fk_column).isNotNull()) \
                .count()
            
            if invalid_fks > 0:
                issues.append({
                    'source': source_name,
                    'check': 'foreign_key',
                    'column': fk_column,
                    'issue': f'{invalid_fks} invalid foreign key values',
                    'severity': 'high'
                })
        
        except Exception as e:
            issues.append({
                'source': source_name,
                'check': 'foreign_key',
                'column': fk_column,
                'issue': f'Error validating: {str(e)}',
                'severity': 'medium'
            })
    
    return issues

def validate_data_types(df, schema_config):
    """Validate that data conforms to expected types."""
    issues = []
    # Add custom data type validation logic here
    return issues

# COMMAND ----------
# Execute validation over Bronze and build cleaned Silver
all_issues = []
validation_results = []

def promote_customers():
    # Clean customers data (from ecommerce-etl-pipeline)
    df = spark.table(f"{CATALOG}.bronze.customers")
    cleaned = df.dropDuplicates(["id"]) \
        .filter(F.col("email").isNotNull()) \
        .filter(F.col("email").rlike("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$")) \
        .withColumn("age_group",
            F.when(F.col("age") < 25, "18-24")
             .when(F.col("age") < 35, "25-34")
             .when(F.col("age") < 45, "35-44")
             .when(F.col("age") < 55, "45-54")
             .when(F.col("age") < 65, "55-64")
             .otherwise("65+")
        ) \
        .withColumn("processing_timestamp", F.current_timestamp())
    cleaned.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.silver.customers")
    print(f"✅ Cleaned {cleaned.count()} customers → {CATALOG}.silver.customers")

def promote_products():
    df = spark.table(f"{CATALOG}.bronze.products")
    cleaned = df.dropDuplicates(["id"]) \
        .filter(F.col("price") > 0) \
        .withColumn("price_tier",
            F.when(F.col("price") < 50, "Budget")
             .when(F.col("price") < 200, "Mid-range")
             .when(F.col("price") < 500, "Premium")
             .otherwise("Luxury")
        ) \
        .withColumn("in_stock", F.col("stock_quantity") > 0) \
        .withColumn("processing_timestamp", F.current_timestamp())
    cleaned.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.silver.products")
    print(f"✅ Cleaned {cleaned.count()} products → {CATALOG}.silver.products")

def promote_orders():
    df = spark.table(f"{CATALOG}.bronze.orders")
    cleaned = df.dropDuplicates(["id"]) \
        .filter(F.col("total_amount") > 0) \
        .filter(F.col("status").isin(["completed", "shipped", "processing", "cancelled"])) \
        .withColumn("order_year", F.year(F.col("order_date"))) \
        .withColumn("order_month", F.month(F.col("order_date"))) \
        .withColumn("order_quarter", F.quarter(F.col("order_date"))) \
        .withColumn("processing_timestamp", F.current_timestamp())
    cleaned.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.silver.orders")
    print(f"✅ Cleaned {cleaned.count()} orders → {CATALOG}.silver.orders")

def promote_reviews():
    df = spark.table(f"{CATALOG}.bronze.reviews")
    cleaned = df.dropDuplicates(["id"]) \
        .filter(F.col("rating").between(1, 5)) \
        .withColumn("sentiment",
            F.when(F.col("rating") >= 4, "Positive")
             .when(F.col("rating") == 3, "Neutral")
             .otherwise("Negative")
        ) \
        .withColumn("processing_timestamp", F.current_timestamp())
    cleaned.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.silver.reviews")
    print(f"✅ Cleaned {cleaned.count()} reviews → {CATALOG}.silver.reviews")

# Iterate configured sources, run validations, then promote with cleaning if source is recognized
for source in sources:
    source_name = source['name']
    bronze_table = f"{CATALOG}.bronze.{source_name}"
    print(f"\n{'='*60}\nValidating Bronze → Silver: {source_name}\nTable: {bronze_table}")
    try:
        df = spark.table(bronze_table)
        record_count = df.count()
        issues = []
        validation_cfg = source.get('validation', {})
        if 'required_columns' in validation_cfg:
            issues.extend(validate_required_columns(df, source_name, validation_cfg['required_columns']))
        if 'unique_columns' in validation_cfg:
            issues.extend(validate_unique_columns(df, source_name, validation_cfg['unique_columns']))
        if 'foreign_keys' in validation_cfg:
            issues.extend(validate_foreign_keys(df, source_name, validation_cfg['foreign_keys']))
        all_issues.extend(issues)
        critical_issues = len([i for i in issues if i['severity'] == 'critical'])
        high_issues = len([i for i in issues if i['severity'] == 'high'])
        quality_score = max(0, min(100, 100 - (critical_issues * 10 + high_issues * 5)))
        status = 'passed' if quality_score >= 90 else ('warning' if quality_score >= 70 else 'failed')
        validation_results.append({'source': source_name,'record_count': record_count,'issues_found': len(issues),'quality_score': quality_score,'status': status})
        if issues:
            print(f"⚠️  Found {len(issues)} issue(s)")
        else:
            print("✅ No issues found")
        print(f"Data Quality Score: {quality_score}%")
    except Exception as e:
        print(f"❌ Error validating {source_name}: {str(e)}")
        validation_results.append({'source': source_name,'status': 'error','error': str(e)})

# Promote with cleaning
print("\n" + "="*60 + "\nPROMOTING TO SILVER LAYER\n" + "="*60)
try:
    promote_customers()
except Exception as e:
    print(f"❌ Customers promotion failed: {e}")
try:
    promote_products()
except Exception as e:
    print(f"❌ Products promotion failed: {e}")
try:
    promote_orders()
except Exception as e:
    print(f"❌ Orders promotion failed: {e}")
try:
    promote_reviews()
except Exception as e:
    print(f"❌ Reviews promotion failed: {e}")

# COMMAND ----------
# Save Validation Report (unchanged)
if dq_config.get('log_validation_errors', True) and all_issues:
    issues_df = spark.createDataFrame(all_issues).withColumn("validation_timestamp", F.current_timestamp())
    report_path = f"{dq_config.get('validation_report_path', '/mnt/data/reports/validation')}/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    issues_df.write.format("delta").mode("overwrite").save(report_path)
    print(f"📊 Validation report saved to: {report_path}")

# COMMAND ----------
# Summary and Exit
results_df = spark.createDataFrame(validation_results)
results_df.show(truncate=False)
passed = len([r for r in validation_results if r.get('status') == 'passed'])
warning = len([r for r in validation_results if r.get('status') == 'warning'])
failed = len([r for r in validation_results if r.get('status') == 'failed'])
print(f"\nTotal sources: {len(validation_results)}")
print(f"✅ Passed: {passed} | ⚠️ Warning: {warning} | ❌ Failed: {failed}")
print(f"\nTotal issues found: {len(all_issues)}")

if failed > 0 and dq_config.get('fail_on_error', False):
    dbutils.notebook.exit(f"FAILED: {failed} source(s) failed validation")
else:
    dbutils.notebook.exit(f"SUCCESS: Silver promotion complete with {len(all_issues)} issue(s)")
