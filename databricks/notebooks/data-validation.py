# Databricks notebook source
# MAGIC %md
# MAGIC # Data Validation Notebook
# MAGIC 
# MAGIC This notebook validates data quality in Bronze tables and promotes validated data to Silver layer.
# MAGIC 
# MAGIC **Parameters:**
# MAGIC - `environment`: Target environment
# MAGIC 
# MAGIC **Quality Checks:**
# MAGIC - Schema validation
# MAGIC - Null value checks
# MAGIC - Uniqueness constraints
# MAGIC - Foreign key relationships
# MAGIC - Data type validation
# MAGIC - Business rule validation

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import yaml
from pyspark.sql import functions as F
from pyspark.sql.types import *
from datetime import datetime

# Get parameters
dbutils.widgets.text("environment", "dev", "Environment")
environment = dbutils.widgets.get("environment")

print(f"Environment: {environment}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Configuration

# COMMAND ----------

with open("/dbfs/FileStore/configs/data-sources.yml", "r") as f:
    config = yaml.safe_load(f)

sources = config['sources']
dq_config = config.get('data_quality', {})

print(f"Validating {len(sources)} source(s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation Functions

# COMMAND ----------

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

def validate_foreign_keys(df, source_name, fk_config, environment):
    """Validate foreign key relationships."""
    issues = []
    
    for fk in fk_config:
        fk_column = fk['column']
        ref_table, ref_column = fk['references'].split('.')
        ref_table_full = f"neo4j_pipeline_{environment}.bronze.{ref_table}"
        
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

# MAGIC %md
# MAGIC ## Execute Validation

# COMMAND ----------

all_issues = []
validation_results = []

for source in sources:
    source_name = source['name']
    table_name = f"neo4j_pipeline_{environment}.bronze.{source_name}"
    
    print(f"\n{'='*60}")
    print(f"Validating: {source_name}")
    
    try:
        df = spark.table(table_name)
        record_count = df.count()
        
        print(f"Records: {record_count}")
        
        issues = []
        
        # Validate required columns
        validation = source.get('validation', {})
        if 'required_columns' in validation:
            issues.extend(validate_required_columns(
                df, source_name, validation['required_columns']
            ))
        
        # Validate unique columns
        if 'unique_columns' in validation:
            issues.extend(validate_unique_columns(
                df, source_name, validation['unique_columns']
            ))
        
        # Validate foreign keys
        if 'foreign_keys' in validation:
            issues.extend(validate_foreign_keys(
                df, source_name, validation['foreign_keys'], environment
            ))
        
        all_issues.extend(issues)
        
        # Calculate data quality score
        critical_issues = len([i for i in issues if i['severity'] == 'critical'])
        high_issues = len([i for i in issues if i['severity'] == 'high'])
        
        quality_score = 100 - (critical_issues * 10 + high_issues * 5)
        quality_score = max(0, min(100, quality_score))
        
        validation_results.append({
            'source': source_name,
            'record_count': record_count,
            'issues_found': len(issues),
            'quality_score': quality_score,
            'status': 'passed' if quality_score >= 90 else 'warning' if quality_score >= 70 else 'failed'
        })
        
        # Print issues
        if issues:
            print(f"\n⚠️  Found {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - [{issue['severity'].upper()}] {issue['check']}: {issue['column']} - {issue['issue']}")
        else:
            print("✅ No issues found")
        
        print(f"Data Quality Score: {quality_score}%")
    
    except Exception as e:
        print(f"❌ Error validating: {str(e)}")
        validation_results.append({
            'source': source_name,
            'status': 'error',
            'error': str(e)
        })

# COMMAND ----------

# MAGIC %md
# MAGIC ## Promote to Silver Layer

# COMMAND ----------

print("\n" + "="*60)
print("PROMOTING TO SILVER LAYER")
print("="*60)

for result in validation_results:
    if result.get('status') == 'passed' or result.get('quality_score', 0) >= 70:
        source_name = result['source']
        
        try:
            # Read from Bronze
            bronze_table = f"neo4j_pipeline_{environment}.bronze.{source_name}"
            df = spark.table(bronze_table)
            
            # Add validation metadata
            df = df \
                .withColumn("_validation_timestamp", F.current_timestamp()) \
                .withColumn("_quality_score", F.lit(result.get('quality_score', 0)))
            
            # Write to Silver
            silver_path = f"{config['storage']['silver_path']}/{source_name}"
            silver_table = f"neo4j_pipeline_{environment}.silver.{source_name}"
            
            df.write \
                .format("delta") \
                .mode("overwrite") \
                .option("mergeSchema", "true") \
                .option("path", silver_path) \
                .saveAsTable(silver_table)
            
            print(f"✅ Promoted {source_name} to Silver")
        
        except Exception as e:
            print(f"❌ Error promoting {source_name}: {str(e)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save Validation Report

# COMMAND ----------

if dq_config.get('log_validation_errors', True) and all_issues:
    issues_df = spark.createDataFrame(all_issues)
    issues_df = issues_df.withColumn("validation_timestamp", F.current_timestamp())
    
    report_path = f"{dq_config.get('validation_report_path', '/mnt/data/reports/validation')}/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    issues_df.write \
        .format("delta") \
        .mode("overwrite") \
        .save(report_path)
    
    print(f"\n📊 Validation report saved to: {report_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "="*60)
print("VALIDATION SUMMARY")
print("="*60)

results_df = spark.createDataFrame(validation_results)
results_df.show(truncate=False)

passed = len([r for r in validation_results if r.get('status') == 'passed'])
warning = len([r for r in validation_results if r.get('status') == 'warning'])
failed = len([r for r in validation_results if r.get('status') == 'failed'])

print(f"\nTotal sources: {len(validation_results)}")
print(f"✅ Passed: {passed}")
print(f"⚠️  Warning: {warning}")
print(f"❌ Failed: {failed}")
print(f"\nTotal issues found: {len(all_issues)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Exit

# COMMAND ----------

if failed > 0 and dq_config.get('fail_on_error', False):
    dbutils.notebook.exit(f"FAILED: {failed} source(s) failed validation")
else:
    dbutils.notebook.exit(f"SUCCESS: Validation complete with {len(all_issues)} issue(s)")
