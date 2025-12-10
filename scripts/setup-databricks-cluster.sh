#!/bin/bash
# Setup Databricks Cluster Script
# Creates or updates Databricks cluster with Neo4j connector

set -e

ENVIRONMENT=${1:-dev}
CLUSTER_NAME="neo4j-pipeline-${ENVIRONMENT}"

echo "🚀 Setting up Databricks cluster for ${ENVIRONMENT}"

# Check prerequisites
if [ -z "$DATABRICKS_HOST" ] || [ -z "$DATABRICKS_TOKEN" ]; then
    echo "❌ Error: DATABRICKS_HOST and DATABRICKS_TOKEN environment variables must be set"
    exit 1
fi

# Load cluster configuration
CONFIG_FILE="configs/cluster-configurations.yml"

# Create cluster JSON configuration
cat > /tmp/cluster-config.json <<EOF
{
  "cluster_name": "${CLUSTER_NAME}",
  "spark_version": "13.3.x-scala2.12",
  "node_type_id": "Standard_DS3_v2",
  "num_workers": 2,
  "autotermination_minutes": 120,
  "spark_conf": {
    "spark.databricks.cluster.profile": "singleNode",
    "spark.master": "local[*]"
  },
  "init_scripts": [
    {
      "workspace": {
        "destination": "/Shared/neo4j-pipeline/init-scripts/neo4j-connector-setup.sh"
      }
    }
  ],
  "libraries": [
    {
      "maven": {
        "coordinates": "org.neo4j:neo4j-connector-apache-spark_2.12:5.2.0_for_spark_3"
      }
    },
    {
      "pypi": {
        "package": "neo4j"
      }
    }
  ]
}
EOF

echo "📦 Creating/updating cluster..."

# Check if cluster exists
CLUSTER_ID=$(databricks clusters list --output JSON | jq -r ".clusters[] | select(.cluster_name==\"${CLUSTER_NAME}\") | .cluster_id" || echo "")

if [ -n "$CLUSTER_ID" ]; then
    echo "Cluster exists with ID: ${CLUSTER_ID}"
    echo "Updating cluster configuration..."
    databricks clusters edit --json-file /tmp/cluster-config.json
else
    echo "Creating new cluster..."
    databricks clusters create --json-file /tmp/cluster-config.json
fi

echo "✅ Cluster setup complete!"

# Cleanup
rm /tmp/cluster-config.json
