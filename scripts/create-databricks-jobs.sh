#!/bin/bash
# Create Databricks Jobs Script
# Creates or updates ETL pipeline jobs in Databricks

set -e

ENVIRONMENT=${1:-dev}

echo "🔧 Creating Databricks jobs for ${ENVIRONMENT}"

# Check prerequisites
if [ -z "$DATABRICKS_HOST" ] || [ -z "$DATABRICKS_TOKEN" ]; then
    echo "❌ Error: DATABRICKS_HOST and DATABRICKS_TOKEN must be set"
    exit 1
fi

# Create ETL Pipeline Job
cat > /tmp/etl-job.json <<EOF
{
  "name": "Neo4j ETL Pipeline - ${ENVIRONMENT}",
  "tasks": [
    {
      "task_key": "csv_ingestion",
      "notebook_task": {
        "notebook_path": "/Shared/neo4j-pipeline/csv-ingestion",
        "base_parameters": {
          "environment": "${ENVIRONMENT}"
        }
      },
      "new_cluster": {
        "spark_version": "13.3.x-scala2.12",
        "node_type_id": "Standard_DS3_v2",
        "num_workers": 2
      }
    },
    {
      "task_key": "data_validation",
      "depends_on": [{"task_key": "csv_ingestion"}],
      "notebook_task": {
        "notebook_path": "/Shared/neo4j-pipeline/data-validation",
        "base_parameters": {
          "environment": "${ENVIRONMENT}"
        }
      },
      "new_cluster": {
        "spark_version": "13.3.x-scala2.12",
        "node_type_id": "Standard_DS3_v2",
        "num_workers": 2
      }
    },
    {
      "task_key": "graph_transformation",
      "depends_on": [{"task_key": "data_validation"}],
      "notebook_task": {
        "notebook_path": "/Shared/neo4j-pipeline/graph-transformation",
        "base_parameters": {
          "environment": "${ENVIRONMENT}"
        }
      },
      "new_cluster": {
        "spark_version": "13.3.x-scala2.12",
        "node_type_id": "Standard_DS3_v2",
        "num_workers": 2
      }
    },
    {
      "task_key": "neo4j_loading",
      "depends_on": [{"task_key": "graph_transformation"}],
      "notebook_task": {
        "notebook_path": "/Shared/neo4j-pipeline/neo4j-loading",
        "base_parameters": {
          "environment": "${ENVIRONMENT}"
        }
      },
      "new_cluster": {
        "spark_version": "13.3.x-scala2.12",
        "node_type_id": "Standard_DS3_v2",
        "num_workers": 2,
        "spark_conf": {
          "neo4j.url": "{{secrets/neo4j/${ENVIRONMENT}-uri}}",
          "neo4j.authentication.basic.username": "{{secrets/neo4j/${ENVIRONMENT}-username}}",
          "neo4j.authentication.basic.password": "{{secrets/neo4j/${ENVIRONMENT}-password}}"
        }
      }
    }
  ],
  "email_notifications": {
    "on_failure": ["pipeline-alerts@example.com"]
  },
  "timeout_seconds": 3600,
  "max_concurrent_runs": 1
}
EOF

echo "Creating ETL job..."
databricks jobs create --json-file /tmp/etl-job.json 2>/dev/null || \
    databricks jobs reset --json-file /tmp/etl-job.json

echo "✅ Jobs created successfully!"

# Cleanup
rm /tmp/etl-job.json
