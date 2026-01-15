# Monitoring and Operations

## Overview

This document describes monitoring, alerting, and operational procedures for the Neo4j + Databricks pipeline.

## Application Insights

Monitor pipeline performance, errors, and custom metrics:
- Request rates and latencies
- Dependency tracking
- Exception tracking
- Custom events and metrics

### Accessing Application Insights

```bash
# View Application Insights resource
az monitor app-insights component show \
  --app <app-insights-name> \
  --resource-group <resource-group-name>
```

## Alerting

Configure alerts as needed through Azure Monitor:
- Job failures
- Performance degradation
- Cost thresholds
- Secret expiration

### Creating Alerts

```bash
# Create metric alert for job failures
az monitor metrics alert create \
  --name databricks-job-failure \
  --resource-group <resource-group-name> \
  --scopes <resource-id> \
  --condition "count > 0" \
  --description "Alert when Databricks jobs fail"
```

## Logging

Centralized logging with Azure Monitor:

```bash
# View recent logs
az monitor activity-log list --resource-group <RG_NAME>

# Query specific logs
az monitor log-analytics query \
  --workspace <WORKSPACE_ID> \
  --analytics-query "traces | where message contains 'error'"
```

## Databricks Monitoring

### Job Monitoring

```bash
# List recent job runs
databricks jobs list-runs --limit 10

# Get specific job run details
databricks jobs get-run --run-id <run-id>
```

### Cluster Monitoring

```bash
# List clusters and their states
databricks clusters list

# Get cluster details
databricks clusters get --cluster-id <cluster-id>
```

## Neo4j Aura Monitoring

### Instance Status

```bash
# Get Aura instance details via API
# First, get OAuth token
curl -X POST 'https://api.neo4j.io/oauth/token' \
  --user "$AURA_CLIENT_ID:$AURA_CLIENT_SECRET" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials'

# Then query instance
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  https://api.neo4j.io/v1/instances/$AURA_INSTANCE_ID
```

### Query Performance

Use Neo4j Browser or Cypher to monitor:

```cypher
// Show running queries
CALL dbms.listQueries();

// Show query statistics
CALL dbms.queryJmx("org.neo4j:*");
```

## Cost Management

### Compute Start/Stop Workflows

Use the provided workflows to manage compute costs:

- **Compute Start**: Starts Databricks cluster and validates connectivity
- **Compute Stop**: Stops Databricks cluster

See [README](../README.md#startstop-workflows) for details.

### Auto-termination

Clusters are configured with auto-termination settings in Terraform:

```hcl
autotermination_minutes = 30  # Adjust as needed
```

## Performance Monitoring

### Key Metrics to Track

1. **Pipeline Execution Time**
   - Monitor job run durations
   - Set alerts for anomalies

2. **Data Volume**
   - Track row counts in tables
   - Monitor data growth trends

3. **Error Rates**
   - Track job failures
   - Monitor data quality issues

4. **Resource Utilization**
   - Cluster CPU/memory usage
   - Storage consumption

### Databricks Job Metrics

```python
# Example: Get job metrics via SDK
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
run = w.jobs.get_run(run_id=<run-id>)
print(f"State: {run.state.life_cycle_state}")
print(f"Duration: {run.execution_duration} ms")
```

## Operational Procedures

### Daily Operations

1. Check job run status
2. Review error logs
3. Verify data freshness
4. Monitor costs

### Weekly Operations

1. Review performance trends
2. Check for failed jobs
3. Validate data quality
4. Review and adjust alerts

### Monthly Operations

1. Cost analysis and optimization
2. Security audit
3. Backup verification
4. Capacity planning

## Health Checks

### Pipeline Health

```bash
# Run integration showcase to validate end-to-end
gh workflow run 07-neo4j-integration-showcase.yml
```

### Connectivity Health

```bash
# Run Compute Start to validate connectivity
gh workflow run compute-start.yml --field cluster_id=<cluster-id>
```

## Troubleshooting

For operational issues, see:
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Validation Guide](VALIDATION.md)

## Dashboard Recommendations

Consider creating dashboards for:
- Pipeline execution metrics
- Data quality metrics
- Cost tracking
- Error rates and alerts

Use Azure Monitor, Databricks notebooks, or third-party tools like Grafana.
