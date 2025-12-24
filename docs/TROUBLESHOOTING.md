# Troubleshooting Guide

Common issues and solutions for the Neo4j-Databricks Azure Pipeline.

## Quick Diagnostics

### Check System Status
```bash
# Check Azure login
az account show

# List workflows
gh run list --limit 5

# View latest run
gh run view
```

## Common Issues

### 1. Authentication Failures

#### Azure Login Failed
**Symptoms:**
```
Error: Failed to authenticate with Azure
```

**Solutions:**
```bash
# Re-authenticate
az login
az account set --subscription <subscription-id>

# Verify credentials
az account show

# Check service principal
az ad sp show --id <client-id>
```

#### Databricks Token Invalid
**Symptoms:**
```
Error: HTTP 403 Forbidden
Error: Invalid authentication token
```

**Solutions:**
```bash
# Generate new token
# 1. Login to Databricks workspace
# 2. User Settings → Access Tokens → Generate New Token
# 3. Copy token
# 4. Update secret
gh secret set DATABRICKS_TOKEN
```

#### Neo4j Connection Failed
**Symptoms:**
```
Error: Unable to establish connection to Neo4j
ServiceUnavailable: Connection refused
```

**Solutions:**
```bash
# Check credentials via API
curl -u $AURA_CLIENT_ID:$AURA_CLIENT_SECRET \
  https://api.neo4j.io/v1/instances

# Verify instance is running in Aura Console
# Test connection via Neo4j Constraints job in Databricks
```

### 2. Terraform Issues

#### State Lock Error
**Symptoms:**
```
Error: Error acquiring the state lock
```

**Solutions:**
```bash
# Force unlock (use carefully!)
cd terraform
terraform force-unlock <lock-id>

# Or wait for lock to expire (usually 2 minutes)
```

#### Resource Already Exists
**Symptoms:**
```
Error: A resource with the ID already exists
```

**Solutions:**
```bash
# Import existing resource
terraform import azurerm_resource_group.main /subscriptions/.../resourceGroups/...

# Or rename resource in code
```

#### Backend Configuration Not Found
**Symptoms:**
```
Error: Backend configuration not found
```

**Solutions:**
```bash
# Create backend storage
az group create --name rg-tfstate --location eastus
az storage account create --name sttfstate$(date +%s) --resource-group rg-tfstate
az storage container create --name tfstate --account-name <account-name>
```

### 3. Databricks Issues

#### Cluster Start Failed
**Symptoms:**
```
Error: Cluster failed to start
INSTANCE_UNREACHABLE
```

**Solutions:**
```bash
# Check cluster configuration
databricks clusters get --cluster-id <cluster-id>

# Check quotas
az vm list-usage --location eastus --output table

# Try different node type
# Edit configs/cluster-configurations.yml
```

#### Notebook Execution Failed
**Symptoms:**
```
Error: Notebook execution failed
CommandExecutionError
```

**Solutions:**
```bash
# Check notebook logs in Databricks UI
# Verify input parameters
# Check data sources exist
# Verify secrets are configured

# Test notebook manually
databricks workspace export /Shared/neo4j-pipeline/csv-ingestion \
  --format SOURCE
```

#### Library Installation Failed
**Symptoms:**
```
Error: Failed to install library
Library installation skipped
```

**Solutions:**
```bash
# Check library exists
pip search neo4j

# Verify cluster has internet access
# Check init script logs
# Try different library version
```

### 4. Data Pipeline Issues

#### Data Validation Failed
**Symptoms:**
```
ValidationError: Required column missing
ForeignKeyError: Invalid reference
```

**Solutions:**
```bash
# Check source data schema
head sample-data/customers.csv

# Verify configuration
cat configs/data-sources.yml

# Check data quality
spark.table("bronze.customers").show()
```

#### Neo4j Load Failed
**Symptoms:**
```
Error: Failed to create nodes
TransientError: Database unavailable
```

**Solutions:**
```bash
# Check Neo4j status
python scripts/configure-neo4j-connection.py --test

# Reduce batch size
# Edit notebook parameter: batch_size=500

# Check Neo4j memory
# Upgrade Neo4j tier if needed
```

### 5. GitHub Actions Issues

#### Workflow Failed to Start
**Symptoms:**
```
Workflow not triggered
No workflows found
```

**Solutions:**
```bash
# Check workflow syntax
gh workflow view deploy-full-pipeline.yml

# Verify Actions are enabled
# Repository Settings → Actions → Allow all actions

# Check branch protection
gh api repos/:owner/:repo/branches/main/protection
```

#### Secret Not Found
**Symptoms:**
```
Error: Secret AZURE_CREDENTIALS not found
```

**Solutions:**
```bash
# List secrets
gh secret list

# Set secret
gh secret set AZURE_CREDENTIALS < credentials.json

# Verify environment access
# Check environment name matches workflow
```

#### Workflow Timeout
**Symptoms:**
```
Error: The job running on runner has exceeded the maximum execution time
```

**Solutions:**
```bash
# Increase timeout in workflow YAML
timeout-minutes: 60

# Or split into smaller jobs
# Use deploy-infrastructure + deploy-pipeline separately
```

### 6. Cost Issues

#### Unexpected High Costs
**Symptoms:**
- Bill higher than expected
- Budget alert triggered

**Solutions:**
```bash
# Check running resources
az resource list --query "[?type=='Microsoft.Compute/virtualMachines']"

# Stop all clusters
gh workflow run cleanup-resources.yml \
  -f environment=dev \
  -f action=stop-clusters \
  -f confirm=CONFIRM

# Review cost analysis
az consumption usage list --start-date 2024-01-01
```

## Diagnostic Commands

### Check Infrastructure
```bash
# List all resources
az resource list --resource-group rg-neo4j-databricks-dev --output table

# Check Databricks workspace
az databricks workspace show --name dbw-neo4j-dev --resource-group rg-neo4j-databricks-dev

# Check storage
az storage account show --name <storage-account-name>
```

### Check Data Pipeline
```bash
# List Databricks jobs
databricks jobs list

# Get job status
databricks jobs get --job-id <job-id>

# List clusters
databricks clusters list

# Get cluster status
databricks clusters get --cluster-id <cluster-id>
```

### Check Logs
```bash
# Workflow logs
gh run view <run-id> --log

# Azure Activity Log
az monitor activity-log list --resource-group rg-neo4j-databricks-dev

# Databricks job logs
databricks runs get --run-id <run-id>
```

## Performance Issues

### Slow Pipeline Execution
**Symptoms:**
- Pipeline takes longer than expected
- Timeouts occur

**Solutions:**
1. **Increase cluster size:**
```yaml
# configs/cluster-configurations.yml
num_workers: 4  # Increase from 2
node_type_id: "Standard_DS4_v2"  # Upgrade node type
```

2. **Optimize data processing:**
```python
# Use partition pruning
df.filter("date >= '2024-01-01'")

# Cache frequently accessed data
df.cache()

# Optimize joins
df.repartition("customer_id")
```

3. **Tune Spark configuration:**
```yaml
spark_conf:
  "spark.sql.adaptive.enabled": "true"
  "spark.sql.adaptive.coalescePartitions.enabled": "true"
```

### Neo4j Load Slow
**Symptoms:**
- Neo4j loading takes hours
- Connection timeouts

**Solutions:**
1. **Increase batch size:**
```python
# In neo4j-loading notebook
batch_size = 5000  # Increase from 1000
```

2. **Use APOC procedures:**
```cypher
CALL apoc.periodic.iterate(
  "UNWIND $nodes AS node RETURN node",
  "MERGE (n:Label {id: node.id}) SET n += node.properties",
  {batchSize: 10000, parallel: true}
)
```

3. **Upgrade Neo4j instance:**
- Professional → Enterprise
- Increase memory: 8GB → 16GB

## Getting Help

### Information to Provide
When reporting issues, include:

1. **Environment details:**
```bash
az --version
python --version
terraform --version
databricks --version
```

2. **Error messages:**
```bash
# Full error output
# Workflow run ID
# Affected resources
```

3. **Steps to reproduce:**
```bash
# Commands run
# Configuration used
# Expected vs actual behavior
```

4. **Logs:**
```bash
# Workflow logs
gh run view <run-id> --log > workflow.log

# Terraform logs
terraform apply -var-file=dev.tfvars 2>&1 | tee terraform.log
```

### Support Channels
- **Documentation:** Review all docs in `/docs`
- **GitHub Issues:** https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/issues
- **Slack:** #neo4j-databricks-support
- **Email:** support@example.com

### Emergency Procedures
For critical production issues:
1. Contact on-call via PagerDuty
2. Post in #incidents Slack channel
3. Start incident bridge
4. Follow runbook procedures

---

**Last Updated:** 2024-01-10
