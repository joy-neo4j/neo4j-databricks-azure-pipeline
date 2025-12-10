# Databricks notebook source
# MAGIC %md
# MAGIC # CSV Data Ingestion Notebook
# MAGIC 
# MAGIC This notebook ingests CSV data from Azure Storage into Databricks Delta tables (Bronze layer).
# MAGIC 
# MAGIC **Parameters:**
# MAGIC - `environment`: Target environment (dev/staging/prod)
# MAGIC - `source_name`: Optional - specific source to ingest
# MAGIC 
# MAGIC **Outputs:**
# MAGIC - Bronze Delta tables in Unity Catalog

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup and Configuration

# COMMAND ----------

import yaml
from pyspark.sql import functions as F
from pyspark.sql.types import *
from datetime import datetime
import os

# Get parameters
dbutils.widgets.text("environment", "dev", "Environment")
dbutils.widgets.text("source_name", "", "Source Name (optional)")

environment = dbutils.widgets.get("environment")
source_name = dbutils.widgets.get("source_name")

print(f"Environment: {environment}")
print(f"Source: {source_name or 'All sources'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Data Source Configuration

# COMMAND ----------

# Load data sources configuration
with open("/dbfs/FileStore/configs/data-sources.yml", "r") as f:
    config = yaml.safe_load(f)

sources = config['sources']
storage_config = config['storage']
processing_config = config['processing']

# Filter sources if specific source requested
if source_name:
    sources = [s for s in sources if s['name'] == source_name]

print(f"Processing {len(sources)} data source(s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Define Schema Functions

# COMMAND ----------

def get_spark_schema(schema_config):
    """Convert YAML schema to Spark StructType."""
    type_mapping = {
        'integer': IntegerType(),
        'long': LongType(),
        'string': StringType(),
        'decimal': DecimalType(18, 2),
        'double': DoubleType(),
        'timestamp': TimestampType(),
        'date': DateType(),
        'boolean': BooleanType()
    }
    
    fields = []
    for col_name, col_type in schema_config.items():
        spark_type = type_mapping.get(col_type, StringType())
        fields.append(StructField(col_name, spark_type, True))
    
    return StructType(fields)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingestion Function

# COMMAND ----------

def ingest_csv_source(source_config):
    """Ingest a single CSV source into Bronze Delta table."""
    source_name = source_config['name']
    source_path = source_config['path']
    
    print(f"\n{'='*60}")
    print(f"Ingesting: {source_name}")
    print(f"Path: {source_path}")
    
    try:
        # Get schema
        spark_schema = get_spark_schema(source_config['schema'])
        
        # Read CSV
        df = spark.read \
            .format("csv") \
            .option("header", "true") \
            .schema(spark_schema) \
            .load(source_path)
        
        # Add metadata columns
        df = df \
            .withColumn("_ingestion_timestamp", F.current_timestamp()) \
            .withColumn("_ingestion_date", F.current_date()) \
            .withColumn("_source_file", F.input_file_name()) \
            .withColumn("_environment", F.lit(environment))
        
        # Show sample
        print(f"Records read: {df.count()}")
        df.show(5)
        
        # Write to Bronze Delta table
        bronze_path = f"{storage_config['bronze_path']}/{source_name}"
        table_name = f"neo4j_pipeline_{environment}.bronze.{source_name}"
        
        df.write \
            .format("delta") \
            .mode("overwrite") \
            .option("mergeSchema", "true") \
            .option("path", bronze_path) \
            .saveAsTable(table_name)
        
        print(f"✅ Successfully ingested to: {table_name}")
        
        return {
            'source': source_name,
            'status': 'success',
            'record_count': df.count(),
            'table': table_name
        }
    
    except Exception as e:
        print(f"❌ Error ingesting {source_name}: {str(e)}")
        return {
            'source': source_name,
            'status': 'failed',
            'error': str(e)
        }

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execute Ingestion

# COMMAND ----------

results = []

for source in sources:
    result = ingest_csv_source(source)
    results.append(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary Report

# COMMAND ----------

print("\n" + "="*60)
print("INGESTION SUMMARY")
print("="*60)

successful = [r for r in results if r['status'] == 'success']
failed = [r for r in results if r['status'] == 'failed']

print(f"\nTotal sources: {len(results)}")
print(f"Successful: {len(successful)}")
print(f"Failed: {len(failed)}")

if successful:
    print("\n✅ Successful ingestions:")
    for r in successful:
        print(f"  - {r['source']}: {r.get('record_count', 0)} records → {r.get('table', '')}")

if failed:
    print("\n❌ Failed ingestions:")
    for r in failed:
        print(f"  - {r['source']}: {r.get('error', 'Unknown error')}")

# Create results DataFrame for downstream tasks
results_df = spark.createDataFrame(results)
results_df.createOrReplaceTempView("ingestion_results")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Checks

# COMMAND ----------

if config.get('data_quality', {}).get('enable_validation', True):
    print("\n" + "="*60)
    print("DATA QUALITY CHECKS")
    print("="*60)
    
    for source in sources:
        table_name = f"neo4j_pipeline_{environment}.bronze.{source['name']}"
        
        try:
            df = spark.table(table_name)
            
            # Check for null values in required columns
            validation = source.get('validation', {})
            required_cols = validation.get('required_columns', [])
            
            print(f"\nChecking: {source['name']}")
            
            for col in required_cols:
                null_count = df.filter(F.col(col).isNull()).count()
                if null_count > 0:
                    print(f"  ⚠️  Column '{col}' has {null_count} null values")
                else:
                    print(f"  ✅ Column '{col}' has no null values")
            
        except Exception as e:
            print(f"  ❌ Error checking {source['name']}: {str(e)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Exit with Status

# COMMAND ----------

if failed:
    dbutils.notebook.exit(f"FAILED: {len(failed)} source(s) failed ingestion")
else:
    dbutils.notebook.exit(f"SUCCESS: {len(successful)} source(s) ingested successfully")
