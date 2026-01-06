# Deployment Guide

## Quick Start (10 minutes)

### Prerequisites Checklist
- [ ] Azure subscription (Owner or Contributor role)
- [ ] GitHub account with Actions enabled
- [ ] Azure CLI installed (`az --version`)
- [ ] GitHub CLI installed (`gh --version`)
- [ ] Neo4j Aura account

### Step 1: Fork Repository (1 min)
```bash
# Fork via GitHub UI or CLI
gh repo fork joy-neo4j/neo4j-databricks-azure-pipeline --clone
cd neo4j-databricks-azure-pipeline
```

### Step 2: Create Azure Service Principal (2 min)
```bash
# Login to Azure
az login

# Create service principal
az ad sp create-for-rbac \
  --name "neo4j-databricks-sp" \
  --role Contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv) \
  --sdk-auth > azure-credentials.json

# Save output for GitHub secrets
cat azure-credentials.json
```

### Step 3: Configure GitHub Secrets (3 min)
```bash
# Authenticate with GitHub
gh auth login

# Set repository secrets
gh secret set AZURE_CREDENTIALS < azure-credentials.json
gh secret set AZURE_SUBSCRIPTION_ID --body "$(az account show --query id -o tsv)"
gh secret set AZURE_TENANT_ID --body "$(az account show --query tenantId -o tsv)"

# Set Databricks secrets (get from Databricks console)
gh secret set DATABRICKS_ACCOUNT_ID --body "YOUR_ACCOUNT_ID"
gh secret set DATABRICKS_TOKEN --body "YOUR_TOKEN"

# Set Neo4j Aura secrets (get from Aura console)
gh secret set AURA_CLIENT_ID --body "YOUR_CLIENT_ID"
gh secret set AURA_CLIENT_SECRET --body "YOUR_CLIENT_SECRET"
```

### Step 4: Branch Protections (optional, 2 min)
```bash
# Via GitHub UI:
# 1. Go to Settings → Branches
# 2. Protect main branch (e.g., required reviewers)
```

### Step 5: Deploy (2 min)
```bash
# Trigger infrastructure provisioning
gh workflow run 02-provision.yml

# Setup data pipeline and sync secrets to Databricks
gh workflow run 06-data-pipeline.yml

# (Optional) Run end-to-end showcase
gh workflow run 07-neo4j-integration-showcase.yml

# (Optional) Stop compute resources for cost optimization
gh workflow run 10-stop-compute.yml --field action=stop-aura --field confirm=CONFIRM

# Monitor progress
gh run watch

# View deployment URL
gh run view --log
```

## Detailed Deployment Steps

### Prerequisites Setup

#### 1. Azure CLI Installation
```bash
# macOS
brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Download from https://aka.ms/installazurecliwindows

# Verify
az --version
```

#### 2. GitHub CLI Installation  
```bash
# macOS
brew install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg

# Windows
winget install --id GitHub.cli

# Verify
gh --version
```

#### 3. Python & Dependencies
```bash
python3 --version  # Should be 3.8+
pip install -r requirements.txt
```

### Deployment
Single environment deployment using the workflows below.

### Deployment Workflows

#### Full Pipeline Deployment
**When to use:** Initial setup, major infrastructure changes

**What it deploys:**
- Azure resource group
- Storage account
- Key Vault
- Log Analytics & App Insights
- Databricks workspace
- Neo4j Aura instance
- Databricks notebooks & jobs

**Duration:** 15-20 minutes

```bash
gh workflow run deploy-full-pipeline.yml
```

#### Infrastructure Only
**When to use:** Infrastructure updates without code changes

**What it deploys:**
- Azure resources via Terraform
- Neo4j Aura instance

**Duration:** 8-12 minutes

```bash
gh workflow run deploy-infrastructure.yml
```

#### Data Pipeline Only
**When to use:** Code updates, notebook changes

**What it deploys:**
- Databricks notebooks
- Job configurations

**Duration:** 5-8 minutes

```bash
gh workflow run deploy-data-pipeline.yml
```

### Post-Deployment Verification

#### 1. Check Infrastructure
```bash
# List resources
az resource list \
  --resource-group rg-neo4j-databricks \
  --output table

# Verify storage account
az storage account show \
  --name $(az storage account list --query "[0].name" -o tsv) \
  --query '{name:name, location:location, tier:sku.tier}'
```

#### 2. Verify Databricks
```bash
# List workspaces
az databricks workspace list --output table

# Get workspace URL
az databricks workspace show \
  --resource-group rg-neo4j-databricks \
  --name dbw-neo4j \
  --query workspaceUrl -o tsv
```

#### 3. Test Neo4j Connection
```bash
# Test connection via Databricks constraints job (manual run in Databricks UI)
# Or verify credentials via API
curl -u $AURA_CLIENT_ID:$AURA_CLIENT_SECRET \
  https://api.neo4j.io/v1/instances
```

#### 4. Run Test Pipeline
```bash
# Trigger ETL job
gh workflow run scheduled-etl.yml

# Monitor execution
gh run watch
```

### Promotion
Use standard GitHub pull requests and branch protections; separate environments are not required.

## Troubleshooting Deployment

### Common Issues

#### 1. Terraform Backend Not Found
**Error:**
```
Error: Backend configuration not found
```

**Solution:**
```bash
# Create Terraform state storage
az group create --name rg-tfstate-dev --location eastus
az storage account create \
  --name sttfstatedev$(openssl rand -hex 3) \
  --resource-group rg-tfstate-dev \
  --sku Standard_LRS
az storage container create \
  --name tfstate \
  --account-name sttfstatedev
```

#### 2. Service Principal Permissions
**Error:**
```
Error: Insufficient privileges to complete the operation
```

**Solution:**
```bash
# Add Owner role (or specific permissions)
az role assignment create \
  --assignee <service-principal-id> \
  --role Owner \
  --scope /subscriptions/<subscription-id>
```

#### 3. Databricks Token Invalid
**Error:**
```
Error: Invalid Databricks token
```

**Solution:**
```bash
# Generate new token in Databricks UI
# Update GitHub secret
gh secret set DATABRICKS_TOKEN
# Enter token when prompted
```

#### 4. Neo4j Connection Failed
**Error:**
```
Error: Unable to connect to Neo4j Aura
```

**Solution:**
```bash
# Verify credentials
echo $AURA_CLIENT_ID
echo $AURA_CLIENT_SECRET

# Test connection
curl -u $AURA_CLIENT_ID:$AURA_CLIENT_SECRET \
  https://api.neo4j.io/v1/instances
```

### Rollback Procedures

#### Rollback Infrastructure
```bash
# 1. Get previous Terraform state
cd terraform
terraform state pull > previous-state.json

# 2. Rollback to previous version
terraform apply -auto-approve
```

#### Rollback Notebooks
```bash
# 1. Get previous version from Git
git log --oneline databricks/notebooks/

# 2. Checkout previous version
git checkout <commit-hash> databricks/notebooks/

# 3. Redeploy
gh workflow run deploy-data-pipeline.yml
```

#### Full Environment Rollback
```bash
# 1. Restore from backup
gh workflow run manage-environments.yml \
  -f action=rollback \
  -f source_environment=dev

# 2. Verify restoration
gh run list --workflow=manage-environments.yml
```

## Maintenance Operations

### Regular Maintenance

#### Weekly
- Review pipeline execution logs
- Check data quality metrics
- Verify secret expiration dates
- Review cost reports

#### Monthly
- Update Databricks runtime
- Rotate access tokens
- Review and optimize costs
- Update documentation

#### Quarterly
- Security audit
- Performance review
- Capacity planning
- Disaster recovery test

### Secret Rotation
```bash
# 1. Generate new credentials
az ad sp credential reset --name neo4j-databricks-sp --years 1

# 2. Update GitHub secrets
gh secret set AZURE_CREDENTIALS < new-credentials.json

# 3. Test deployment
gh workflow run deploy-infrastructure.yml

# 4. Revoke old credentials (after verification)
```

### Cost Optimization
```bash
# Stop Databricks clusters
gh workflow run 10-stop-compute.yml \
  -f action=stop-dbx-clusters \
  -f confirm=CONFIRM

# Pause Aura instance (uses /instances/{id}/pause with tenant-aware fallback)
gh workflow run 10-stop-compute.yml \
  -f action=stop-aura \
  -f confirm=CONFIRM

# Cleanup temporary resources
gh workflow run 10-stop-compute.yml \
  -f action=cleanup-temp \
  -f confirm=CONFIRM
```

**Aura Pause Endpoint Details:**
- The workflow uses the Neo4j Aura `/instances/{instanceId}/pause` endpoint
- If the request returns 403 or 404 and `AURA_TENANT_ID` is provided, automatically retries using `/tenants/{tenantId}/instances/{instanceId}/pause`
- Gracefully skips (exit 0) if instance is not found (404), already paused (409), or endpoint forbidden (403) after tenant fallback
- Fails only on missing credentials or non-recoverable errors

## Advanced Configuration

### Custom Terraform Backend
```hcl
# terraform/backend.tf
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-tfstate-prod"
    storage_account_name = "sttfstateprod"
    container_name       = "tfstate"
    key                  = "neo4j-databricks.tfstate"
  }
}
```

### Custom Databricks Cluster
```yaml
# configs/cluster-configurations.yml
custom:
  node_type_id: "Standard_DS5_v2"
  num_workers: 10
  spark_conf:
    "spark.custom.config": "value"
```

### Variables
```bash
# .env file (never commit!)
DATABRICKS_HOST=https://...
DATABRICKS_TOKEN=dapi...
NEO4J_URI=neo4j+s://...
```

## Monitoring Deployment

### View Logs
```bash
# Real-time logs
gh run watch

# Specific run
gh run view <run-id> --log

# Failed jobs only
gh run view <run-id> --log-failed
```

### Check Status
```bash
# List recent runs
gh run list --workflow=deploy-full-pipeline.yml

# Run details
gh run view <run-id>
```

### Debugging
```bash
# Enable debug logging
gh workflow run deploy-full-pipeline.yml \
  -f environment=dev \
  -f debug=true

# Download artifacts
gh run download <run-id>
```

## Support

### Getting Help
1. Check [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review workflow logs
3. Search [GitHub Issues](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/issues)
4. Create new issue with:
   - Environment details
   - Error messages
   - Workflow run ID
   - Steps to reproduce

---

**Last Updated:** 2024-01-10  
**Version:** 1.0.0
