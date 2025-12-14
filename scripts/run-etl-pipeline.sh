#!/bin/bash
# Run ETL Pipeline Script
# Triggers the ETL pipeline job in Databricks

set -euo pipefail

ENVIRONMENT=${1:-prod}
JOB_NAME="Neo4j ETL Pipeline - ${ENVIRONMENT}"

echo "🚀 Running ETL Pipeline for ${ENVIRONMENT}"

# Check prerequisites
if [ -z "${DATABRICKS_HOST:-}" ] || [ -z "${DATABRICKS_TOKEN:-}" ]; then
    echo "❌ Error: DATABRICKS_HOST and DATABRICKS_TOKEN must be set"
    exit 1
fi
if [ -z "${NEO4J_URI:-}" ] || [ -z "${NEO4J_USER:-}" ] || [ -z "${NEO4J_PASSWORD:-}" ]; then
    echo "❌ Error: NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set"
    exit 1
fi

# Find job ID
echo "🔍 Finding job ID..."
JOB_ID=$(databricks jobs list --output JSON | jq -r ".jobs[] | select(.settings.name==\"${JOB_NAME}\") | .job_id" || echo "")

if [ -z "$JOB_ID" ]; then
    echo "❌ Error: Job '${JOB_NAME}' not found"
    echo "Run: ./scripts/create-databricks-jobs.sh ${ENVIRONMENT}"
    exit 1
fi

echo "Found job ID: ${JOB_ID}"

# Trigger job run
echo "▶️  Triggering job run..."
RUN_ID=$(databricks jobs run-now --job-id "${JOB_ID}" --output JSON | jq -r '.run_id')

echo "✅ Job triggered successfully!"
echo "   Run ID: ${RUN_ID}"
echo "   View in Databricks: ${DATABRICKS_HOST}/#job/${JOB_ID}/run/${RUN_ID}"

# Optional: Wait for completion
if [ "${WAIT_FOR_COMPLETION}" = "true" ]; then
    echo "⏳ Waiting for job to complete..."
    
    while true; do
        STATUS=$(databricks runs get --run-id "${RUN_ID}" --output JSON | jq -r '.state.life_cycle_state')
        
        if [ "$STATUS" = "TERMINATED" ]; then
            RESULT=$(databricks runs get --run-id "${RUN_ID}" --output JSON | jq -r '.state.result_state')
            if [ "$RESULT" = "SUCCESS" ]; then
                echo "✅ Job completed successfully!"
                exit 0
            else
                echo "❌ Job failed with result: ${RESULT}"
                exit 1
            fi
        fi
        
        echo "   Status: ${STATUS}"
        sleep 30
    done
fi
