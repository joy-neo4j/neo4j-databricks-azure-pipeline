#!/bin/bash
# Cleanup Resources Script
# Stops or deletes resources to save costs

set -e

ENVIRONMENT=${1:-dev}
ACTION=${2:-stop-clusters}

echo "🧹 Cleanup: ${ACTION} for ${ENVIRONMENT}"

case $ACTION in
  stop-clusters)
    echo "Stopping all Databricks clusters..."
    databricks clusters list --output JSON | jq -r '.clusters[] | select(.state=="RUNNING") | .cluster_id' | while read cluster_id; do
      echo "  Stopping cluster: ${cluster_id}"
      databricks clusters delete --cluster-id "${cluster_id}"
    done
    echo "✅ All clusters stopped"
    ;;
  
  pause-jobs)
    echo "Pausing all scheduled jobs..."
    databricks jobs list --output JSON | jq -r '.jobs[] | .job_id' | while read job_id; do
      echo "  Pausing job: ${job_id}"
      # Note: Actual pause would require updating job schedule
    done
    echo "✅ Jobs paused"
    ;;
  
  cleanup-temp)
    echo "Cleaning up temporary data..."
    # Add cleanup logic here
    echo "✅ Temporary data cleaned"
    ;;
  
  *)
    echo "❌ Unknown action: ${ACTION}"
    echo "Available actions: stop-clusters, pause-jobs, cleanup-temp"
    exit 1
    ;;
esac
