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

# Monitor progress
gh run watch

# View deployment URL
gh run view --log
```

### Step 6: Start/Stop Compute (optional)
```bash
# Start a specific Databricks cluster (validates Neo4j connectivity)
gh workflow run compute-start.yml --field cluster_id=YOUR_CLUSTER_ID

# Stop a specific Databricks cluster
gh workflow run compute-stop.yml --field cluster_id=YOUR_CLUSTER_ID

# Or use unified workflow for all compute operations:
# Start cluster
gh workflow run 10-stop-compute.yml --field action=start-dbx-cluster --field cluster_id=YOUR_CLUSTER_ID --field confirm=CONFIRM

# Stop all running clusters
gh workflow run 10-stop-compute.yml --field action=stop-dbx-clusters --field confirm=CONFIRM

# Start Aura instance
gh workflow run 10-stop-compute.yml --field action=start-aura --field confirm=CONFIRM

# Stop Aura instance
gh workflow run 10-stop-compute.yml --field action=stop-aura --field confirm=CONFIRM
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

#### 1. Prerequisites Setup (Optional)
**File:** `.github/workflows/01-prerequisites-setup.yml`  
**When to use:** Pre-deployment validation  
**Duration:** 2-3 minutes

**What it validates:**
- Azure credentials
- Databricks token
- Neo4j Aura credentials

```bash
gh workflow run 01-prerequisites-setup.yml
```

#### 2. Provision Infrastructure
**File:** `.github/workflows/02-provision.yml`  
**When to use:** Initial setup or infrastructure updates  
**Duration:** 10-15 minutes

**What it deploys:**
- Azure infrastructure (Resource Group, Storage, Key Vault, Databricks workspace)
- Neo4j Aura instance with credentials in Key Vault
- Databricks cluster with Neo4j Spark Connector
- Unity Catalog schemas (bronze, silver, gold, graph_ready)
- Databricks notebooks uploaded to workspace
- Databricks jobs (ETL pipeline)
- Key Vault-backed secret scope

```bash
gh workflow run 02-provision.yml
```

#### 3. Data Pipeline Setup
**File:** `.github/workflows/06-data-pipeline.yml`  
**When to use:** Secrets synchronization and notebook validation  
**Duration:** 2-3 minutes

**What it does:**
- Validates notebook syntax and Python compilation
- Creates Databricks secret scope "pipeline-secrets"
- Syncs Neo4j/Aura credentials from GitHub secrets to Databricks

```bash
gh workflow run 06-data-pipeline.yml
```

#### 4. Neo4j Integration Showcase (Optional)
**File:** `.github/workflows/07-neo4j-integration-showcase.yml`  
**When to use:** End-to-end pipeline validation  
**Duration:** 10-15 minutes

**What it executes:**
- Complete e-commerce pipeline from ingestion to Neo4j
- Data validation and graph transformation
- Neo4j loading and write-back operations

```bash
gh workflow run 07-neo4j-integration-showcase.yml
```

#### 5. Start/Stop Compute Management

**Standalone Workflows:**

**File:** `.github/workflows/compute-start.yml`  
Start a specific Databricks cluster and validate Neo4j connectivity:
```bash
gh workflow run compute-start.yml --field cluster_id=YOUR_CLUSTER_ID
```

**File:** `.github/workflows/compute-stop.yml`  
Stop a specific Databricks cluster:
```bash
gh workflow run compute-stop.yml --field cluster_id=YOUR_CLUSTER_ID
```

**Unified Workflow:**

**File:** `.github/workflows/10-stop-compute.yml`  
**When to use:** Manage all compute resources from one workflow  
**Duration:** 1-2 minutes

**Available actions:**
- `start-dbx-cluster`: Start specific cluster by ID with Neo4j validation
- `stop-dbx-clusters`: Stop all running clusters
- `start-aura`: Resume Neo4j Aura instance
- `stop-aura`: Pause Neo4j Aura instance

```bash
# Start cluster
gh workflow run 10-stop-compute.yml \
  --field action=start-dbx-cluster \
  --field cluster_id=YOUR_CLUSTER_ID \
  --field confirm=CONFIRM

# Stop all clusters
gh workflow run 10-stop-compute.yml \
  --field action=stop-dbx-clusters \
  --field confirm=CONFIRM

# Start Aura
gh workflow run 10-stop-compute.yml \
  --field action=start-aura \
  --field confirm=CONFIRM

# Stop Aura
gh workflow run 10-stop-compute.yml \
  --field action=stop-aura \
  --field confirm=CONFIRM
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
# Trigger showcase workflow for end-to-end validation
gh workflow run 07-neo4j-integration-showcase.yml

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
gh workflow run 06-data-pipeline.yml
```

#### Full Environment Rollback
```bash
# 1. Revert to previous infrastructure state
cd terraform
git checkout <previous-commit>
terraform plan
terraform apply

# 2. Verify restoration
gh workflow run 02-provision.yml
gh run watch
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
gh workflow run 02-provision.yml

# 4. Revoke old credentials (after verification)
```

### Cost Optimization
```bash
# Stop Databricks clusters
gh workflow run 10-stop-compute.yml \
  -f action=stop-dbx-clusters \
  -f confirm=CONFIRM

# Pause Aura instance (OAuth 2.0 Bearer token auth; strict HTTP 202)
gh workflow run 10-stop-compute.yml \
  -f action=stop-aura \
  -f confirm=CONFIRM

# Cleanup temporary resources
gh workflow run 10-stop-compute.yml \
  -f action=cleanup-temp \
  -f confirm=CONFIRM
```

**Aura Pause Endpoint Details:**
- The workflow uses OAuth 2.0 client credentials flow to obtain a Bearer access token from `https://api.neo4j.io/oauth/token`
- The Bearer token is then used to authenticate API calls to the Neo4j Aura `/instances/{instanceId}/pause` endpoint
- If the request returns 403 or 404 and `AURA_TENANT_ID` is provided, automatically retries using `/tenants/{tenantId}/instances/{instanceId}/pause`
- Enforces strict HTTP 202 success: any response code other than 202 will fail the workflow
- Fails on missing credentials or any non-202 response

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
# List recent runs for provision workflow
gh run list --workflow=02-provision.yml

# Run details
gh run view <run-id>
```

### Debugging
```bash
# View workflow logs
gh run view <run-id> --log

# Download artifacts (if any)
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

## Multi-Environment Deployment

### Overview
Deploy multiple isolated environments (dev, staging, prod) in the same Azure subscription while sharing a Databricks workspace to optimize costs.

### Option 1: Reuse Existing Databricks Workspace

**Use Case**: Deploy a second environment (e.g., dev) in the same subscription while reusing an existing Databricks workspace.

#### Step 1: Prepare Environment-Specific Configuration
```bash
# Create a separate tfvars file for the new environment
cd terraform
cp terraform.tfvars.example dev.tfvars
```

#### Step 2: Edit dev.tfvars
```hcl
# Resource Group (new for this environment)
resource_group_name = "rg-neo4j-dbx-dev"
location = "uksouth"

# Reuse existing Databricks workspace
create_databricks_workspace = false
databricks_workspace_name = "dbw-neo4j-prod"  # Reference existing workspace

# Isolated Unity Catalog for this environment
catalog_name_override = "neo4j_pipeline_dev"

# Separate storage for this environment
storage_account_name = null  # Auto-generates unique name
storage_container_name = "pipeline-data-dev"

# Environment-specific Neo4j settings (optional - creates new Aura instance)
neo4j_region = "uksouth"
neo4j_tier = "professional"
neo4j_memory = "8GB"
```

#### Step 3: Deploy Dev Environment
```bash
# Option A: Using Terraform directly
terraform plan -var-file="dev.tfvars" -out=dev.tfplan
terraform apply dev.tfplan

# Option B: Using Terraform workspaces
terraform workspace new dev
terraform plan -var-file="dev.tfvars"
terraform apply -var-file="dev.tfvars"
```

#### Step 4: Configure GitHub Secrets for Dev Environment
```bash
# Set dev-specific secrets (optional - for GitHub Actions)
gh secret set DEV_RESOURCE_GROUP_NAME --body "rg-neo4j-dbx-dev"
gh secret set DEV_CATALOG_NAME --body "neo4j_pipeline_dev"
gh secret set DEV_NEO4J_URI --body "neo4j+s://xxx.databases.neo4j.io"
```

#### Step 5: Update Workflow for Dev Environment
```yaml
# In .github/workflows/07-neo4j-integration-showcase.yml
# Add environment-specific inputs
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        type: choice
        options:
          - dev
          - prod
        default: 'dev'

# Use environment-specific catalog
env:
  CATALOG_NAME: ${{ inputs.environment == 'dev' && 'neo4j_pipeline_dev' || 'neo4j_pipeline' }}
```

### Benefits of This Approach

1. **Cost Efficiency**: Share Databricks workspace license and infrastructure costs
2. **Resource Isolation**: Each environment has its own:
   - Azure Resource Group
   - Storage Account
   - Unity Catalog
   - Neo4j Aura instance (optional)
3. **Data Separation**: Complete isolation via separate Unity Catalogs
4. **Easy Cleanup**: Delete entire Resource Group to remove environment
5. **Flexible Configuration**: Mix and match shared and isolated resources

### Environment Comparison

| Resource | Shared | Isolated |
|----------|--------|----------|
| Databricks Workspace | ✅ | |
| Resource Group | | ✅ |
| Storage Account | | ✅ |
| Unity Catalog | | ✅ |
| Neo4j Aura | | ✅ |
| Key Vault | | ✅ |

### Cleanup Dev Environment
```bash
# Option 1: Using Terraform
cd terraform
terraform workspace select dev
terraform destroy -var-file="dev.tfvars"

# Option 2: Delete Resource Group directly
az group delete --name rg-neo4j-dbx-dev --yes --no-wait
```

---

**Last Updated:** 2024-01-10  
**Version:** 1.0.0
