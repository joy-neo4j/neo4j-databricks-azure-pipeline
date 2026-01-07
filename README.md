# Neo4j + Databricks E-commerce Analytics Pipeline

[![Provision Infrastructure](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/actions/workflows/02-provision.yml/badge.svg)](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/actions/workflows/02-provision.yml)

A production-ready, single-click deployment solution for **e-commerce analytics** using Azure Databricks and Neo4j Aura. Features comprehensive graph-based customer journey analysis, product recommendations, and supply chain optimization with Neo4j Spark Connector 5.3.0 optimized for UK South region.

## 🚀 Features

### E-commerce Analytics Capabilities
- **Customer 360 View**: Complete customer journey analysis with purchase history and preferences
- **Product Recommendations**: Collaborative filtering and graph-based recommendation engine
- **Supply Chain Analytics**: Supplier performance tracking and inventory optimization
- **Neo4j Graph Integration**: High-performance batch loading with Spark Connector 5.3.0
- **UK South Optimization**: Regional deployment for data residency and GDPR compliance

### Infrastructure & Deployment
- **Consolidated Provisioning**: Single Terraform workflow deploys Azure + Databricks + Aura + Unity Catalog
- **Infrastructure as Code**: Complete infrastructure and pipeline deployment in one apply
- **Terraform-Managed Jobs**: Databricks jobs, notebooks, and clusters defined in Terraform
- **Enhanced Secrets Management**: GitHub secrets + Azure Key Vault integration with fallback mechanisms
- **Cost Optimization**: Auto-pause, scheduling, and resource cleanup capabilities
- **Comprehensive Monitoring**: Application Insights, alerting, and performance tracking

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Prerequisite Permissions](#-prerequisite-permissions)
- [Quick Start](#-quick-start)
- [Secrets Configuration](#-secrets-configuration)
- [Deployment Workflows](#-deployment-workflows)
- [Architecture](#-architecture)
- [Configuration](#-configuration)
- [Monitoring and Operations](#-monitoring-and-operations)
- [Troubleshooting](#-troubleshooting)
- [Validation](#-validation)
- [Contributing](#-contributing)
- [Version History](#-version-history)

## 🔧 Prerequisites

### Required Tools
- Azure subscription with appropriate permissions (see [Prerequisite Permissions](#-prerequisite-permissions))
- GitHub account with Actions enabled
- Azure CLI (version 2.40+)
- Terraform (version 1.5+)
- Python 3.8+

### Azure Services
- **Existing Azure Databricks workspace** (Premium or Enterprise tier recommended)
  - Workspace URL should be provided via `DATABRICKS_HOST` secret
  - Set `create_databricks_workspace = false` in Terraform variables (default)
  - Alternatively, set `create_databricks_workspace = true` to create a new workspace
- Azure Resource Manager
- Azure Key Vault (for production secrets)
- Azure Monitor and Application Insights

### Neo4j Aura
- Neo4j Aura account (Professional or Enterprise tier)
- Aura API credentials

## 🔐 Prerequisite Permissions

This section documents the specific roles and permissions required for deployment. Note that generic "Contributor" access is **not recommended** for production environments.

### Azure Service Principal Permissions

The Azure Service Principal used by GitHub Actions requires the following specific role assignments:

#### 1. Networking Permissions (for VNet/Subnet/NSG changes)
```bash
# Network Contributor role for networking resources
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Network Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>
```

#### 2. Storage Permissions (for Data Lake and Blob Storage)
```bash
# Storage Blob Data Contributor for storage account operations
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>/providers/Microsoft.Storage/storageAccounts/<STORAGE_ACCOUNT_NAME>

# Storage Account Contributor for storage account management
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Storage Account Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>/providers/Microsoft.Storage/storageAccounts/<STORAGE_ACCOUNT_NAME>
```

#### 3. Key Vault Permissions (for secrets management)
```bash
# Key Vault Administrator for managing secrets
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Key Vault Administrator" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>/providers/Microsoft.KeyVault/vaults/<KEY_VAULT_NAME>

# Alternatively, use Key Vault Secrets Officer for limited secret management
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Key Vault Secrets Officer" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>/providers/Microsoft.KeyVault/vaults/<KEY_VAULT_NAME>
```

#### 4. Resource Group Management
```bash
# Owner role at resource group level for full resource management
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Owner" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>
```

#### 5. Azure Databricks Workspace Access (if creating new workspace)
```bash
# Only required if create_databricks_workspace = true
# Databricks workspace requires Owner or Contributor at resource group level
# This is handled by the Owner role assignment above
```

#### 6. Monitoring and Logging
```bash
# Log Analytics Contributor for monitoring setup
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Log Analytics Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>

# Application Insights Component Contributor
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Application Insights Component Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>
```

### Databricks Personal Access Token (PAT) User Permissions

The Databricks PAT user requires the following permissions for Unity Catalog operations:

#### 1. Workspace Admin Role
The PAT user should have **Workspace Admin** privileges to manage clusters, jobs, and notebooks:

```bash
# Grant workspace admin via Databricks UI:
# Settings → Admin Console → Users → Select User → Role: Admin
```

#### 2. Unity Catalog Metastore Permissions

```sql
-- Grant CREATE on metastore (execute in Databricks SQL editor)
GRANT CREATE CATALOG ON METASTORE TO `<user_email>`;
GRANT CREATE SCHEMA ON CATALOG <catalog_name> TO `<user_email>`;
GRANT CREATE TABLE ON CATALOG <catalog_name> TO `<user_email>`;
```

#### 3. Catalog-Level Permissions
```sql
-- Grant full permissions on the catalog
GRANT ALL PRIVILEGES ON CATALOG <catalog_name> TO `<user_email>`;

-- Grant usage on catalog (minimum required)
GRANT USAGE ON CATALOG <catalog_name> TO `<user_email>`;
```

#### 4. Schema-Level Permissions
```sql
-- Grant permissions on specific schemas
GRANT CREATE, USAGE, SELECT, MODIFY ON SCHEMA <catalog_name>.bronze TO `<user_email>`;
GRANT CREATE, USAGE, SELECT, MODIFY ON SCHEMA <catalog_name>.silver TO `<user_email>`;
GRANT CREATE, USAGE, SELECT, MODIFY ON SCHEMA <catalog_name>.gold TO `<user_email>`;
GRANT CREATE, USAGE, SELECT, MODIFY ON SCHEMA <catalog_name>.graph_ready TO `<user_email>`;
```

#### 5. Storage Credential and External Location Permissions (for Unity Catalog)
```sql
-- Grant permissions to manage storage credentials
GRANT CREATE STORAGE CREDENTIAL ON METASTORE TO `<user_email>`;
GRANT CREATE EXTERNAL LOCATION ON METASTORE TO `<user_email>`;

-- Grant access to specific external location
GRANT READ FILES, WRITE FILES ON EXTERNAL LOCATION `<location_name>` TO `<user_email>`;
```

#### 6. Cluster Management Permissions
The PAT user needs **Can Manage** permission on clusters:

```bash
# Via Databricks UI:
# Compute → Select Cluster → Permissions → Add User → Permission: Can Manage
```

#### 7. Secret Scope Permissions
```bash
# Grant permissions on secret scopes (via Databricks CLI)
databricks secrets put-acl \
  --scope neo4j \
  --principal <user_email> \
  --permission MANAGE
```

### Minimum Required Permissions Summary

For a **production deployment with existing Databricks workspace** (`create_databricks_workspace = false`):

**Azure Service Principal:**
- Resource Group: `Owner` (for resource management)
- Storage: `Storage Blob Data Contributor` + `Storage Account Contributor`
- Key Vault: `Key Vault Secrets Officer` (minimum) or `Key Vault Administrator`
- Networking: `Network Contributor` (if using private endpoints)
- Monitoring: `Log Analytics Contributor` + `Application Insights Component Contributor`

**Databricks PAT User:**
- Workspace: `Admin` role
- Unity Catalog: `USAGE`, `CREATE`, `SELECT`, `MODIFY` on catalog and schemas
- Clusters: `Can Manage` permission
- Secret Scopes: `MANAGE` permission on `neo4j` scope

### Verification Commands

```bash
# Verify Service Principal role assignments
az role assignment list \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --output table

# Verify Service Principal has access to Key Vault
az keyvault secret list \
  --vault-name <KEY_VAULT_NAME> \
  --query "[].name" \
  --output table

# Verify Databricks workspace access
databricks workspace list --profile <profile_name>

# Test Unity Catalog access (via Databricks SQL)
SHOW CATALOGS;
SHOW SCHEMAS IN CATALOG <catalog_name>;
```

## 🏃 Quick Start

### 1. Fork and Clone Repository
```bash
git clone https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline.git
cd neo4j-databricks-azure-pipeline
```

### 2. Configure GitHub Secrets

#### Required Repository Secrets
```bash
# Azure Authentication
AZURE_CREDENTIALS        # Service principal JSON
AZURE_SUBSCRIPTION_ID    # Azure subscription ID
AZURE_TENANT_ID         # Azure AD tenant ID

# Databricks
DATABRICKS_HOST         # Existing Databricks workspace URL (e.g., https://adb-xxx.azuredatabricks.net)
DATABRICKS_TOKEN        # Personal access token

# Neo4j Database
NEO4J_URI              # Neo4j connection URI (e.g., neo4j+s://xxxxx.databases.neo4j.io)
NEO4J_USERNAME         # Neo4j username (typically 'neo4j')
NEO4J_PASSWORD         # Neo4j password

# Neo4j Aura API (for instance management)
AURA_CLIENT_ID          # Aura API client ID
AURA_CLIENT_SECRET      # Aura API client secret
```

#### Optional Secrets
```bash
AURA_INSTANCE_ID        # Aura instance ID (for stop-aura workflow action)
AURA_TENANT_ID          # Aura tenant ID (for tenant-aware Aura API fallback)
```

**Note:** Neo4j and Aura credentials are automatically synchronized to Databricks secret scope "pipeline-secrets" by the `06-data-pipeline.yml` workflow.

See [SECRETS_MANAGEMENT.md](docs/SECRETS_MANAGEMENT.md) for detailed setup instructions.

### 3. Create Azure Service Principal

First, create the service principal without role assignment:

```bash
az login
az ad sp create-for-rbac \
  --name "neo4j-databricks-pipeline" \
  --skip-assignment \
  --sdk-auth
```

Copy the JSON output to the `AZURE_CREDENTIALS` secret.

**Important:** After creating the service principal, assign the specific roles documented in the [Prerequisite Permissions](#-prerequisite-permissions) section above. Do not use the generic "Contributor" role for production deployments.

### 4. Configure Terraform Variables (Optional)

Create `terraform/terraform.tfvars` from the example:
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your environment-specific values
```

### 5. Deploy

#### Automated Deployment via GitHub Actions

Navigate to the Actions tab in your repository and run workflows in sequence:
```bash
# 1. Provision complete infrastructure (Azure + Databricks + Aura + Unity Catalog)
gh workflow run 02-provision.yml

# 2. Setup Databricks secrets and validate data pipeline notebooks
gh workflow run 06-data-pipeline.yml

# 3. Run end-to-end showcase (optional)
gh workflow run 07-neo4j-integration-showcase.yml
```

**Note**: 
- The `02-provision.yml` workflow consolidates infrastructure deployment into a single Terraform run.
- The `06-data-pipeline.yml` workflow synchronizes Neo4j/Aura credentials from GitHub secrets to Databricks secret scope "pipeline-secrets".

### 6. Verify Deployment
```bash
# Check deployment status
gh run list --workflow=02-provision.yml

# View logs
gh run view <run-id> --log

# Check Terraform outputs
cd terraform
terraform output
```

## 🔐 Secrets Configuration

### Repository-Level Secrets
Store in **Settings → Secrets and variables → Actions → Repository secrets**:

```yaml
# Core Infrastructure
AZURE_CREDENTIALS:
  {
    "clientId": "xxx",
    "clientSecret": "xxx",
    "subscriptionId": "xxx",
    "tenantId": "xxx"
  }

AZURE_SUBSCRIPTION_ID: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
AZURE_TENANT_ID: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Databricks
DATABRICKS_ACCOUNT_ID: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
DATABRICKS_TOKEN: "dapixxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Neo4j Aura
AURA_CLIENT_ID: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
AURA_CLIENT_SECRET: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### Environment-Specific Secrets
Store in **Settings → Environments → [environment] → Environment secrets**:

```yaml
# Production-specific overrides
PROD_AZURE_CREDENTIALS: # Production service principal
PROD_DATABRICKS_TOKEN: # Production PAT
PROD_KEY_VAULT_NAME: # Azure Key Vault name
```

### Secret Fallback Mechanism
The system automatically falls back to repository secrets if environment-specific secrets are not found:
1. Check `{ENV}_AZURE_CREDENTIALS`
2. Fall back to `AZURE_CREDENTIALS`
3. Fail with clear error message if neither exists

See [docs/SECRETS_MANAGEMENT.md](docs/SECRETS_MANAGEMENT.md) for advanced configuration.

## 🔄 Deployment Workflows

### Consolidated Terraform Deployment

#### 1. Prerequisites Setup (Optional)
**File**: `.github/workflows/01-prerequisites-setup.yml`
- **Duration**: 2-3 minutes
- **Validates**: Azure credentials, Databricks token, Neo4j Aura credentials
- **Use Case**: Pre-deployment validation and compatibility checks

#### 2. Provision (Consolidated Infrastructure)
**File**: `.github/workflows/02-provision.yml`
- **Duration**: 10-15 minutes
- **Deploys via Terraform**:
  - Azure infrastructure (Resource Group, Storage, Key Vault, Databricks workspace)
  - Neo4j Aura instance with credentials stored in Key Vault
  - Databricks cluster with Neo4j Spark Connector 5.3.0
  - Unity Catalog schemas (bronze, silver, gold, graph_ready)
  - Databricks notebooks uploaded to workspace
  - Databricks jobs (ETL pipeline with 6 tasks)
  - Key Vault-backed secret scope for Neo4j credentials
  - Unity Catalog grants for users
- **Use Case**: Complete infrastructure and pipeline deployment in one workflow
- **Note**: Consolidates the functionality of previous workflows 02-05

#### 3. Data Pipeline Validation and Secrets Setup
**File**: `.github/workflows/06-data-pipeline.yml`
- **Duration**: 2-3 minutes
- **Validates**: Notebook syntax and Python compilation
- **Secrets Setup**: Creates Databricks secret scope "pipeline-secrets" and populates Neo4j/Aura credentials from GitHub secrets
- **Use Case**: Syntax validation for notebooks and secrets synchronization (deployment handled by Terraform)

#### 4. Neo4j Integration Showcase (Optional)
**File**: `.github/workflows/07-neo4j-integration-showcase.yml`
- **Duration**: 10-15 minutes
- **Executes**: Complete e-commerce pipeline from ingestion to Neo4j
- **Use Case**: End-to-end pipeline validation and showcase

#### 5. Stop Compute (Cost Management)
**File**: `.github/workflows/10-stop-compute.yml`
- **Duration**: 1-2 minutes
- **Actions**: Stop Databricks clusters, pause Aura instance, or cleanup temporary resources
- **Aura Pause**: Uses OAuth 2.0 Bearer token authentication to call `/instances/{instanceId}/pause` endpoint with tenant-aware fallback to `/tenants/{tenantId}/instances/{instanceId}/pause`; enforces strict HTTP 202 success (fails on any other response code); fails on missing credentials
- **Use Case**: Manual cost optimization by stopping compute resources when not needed

### Legacy Workflows (Deprecated)
The following workflows have been consolidated into `02-provision.yml`:
- `02-azure-infrastructure.yml.deprecated`
- `03-neo4j-aura-setup.yml.deprecated`
- `04-databricks-configuration.yml.deprecated`
- `05-unity-catalog-setup.yml.deprecated`

## 🏗️ Architecture

### E-commerce Data Model

#### Graph Schema
```
┌──────────┐         PURCHASED         ┌──────────┐
│ Customer ├────────────────────────────> Product │
└────┬─────┘                            └────┬─────┘
     │                                       │
     │ REVIEWED                              │ BELONGS_TO
     │                                       │
     └──────────────────────────────────────> Category │
                                         └──────────┘
                                              │
                                              │ SUPPLIES
                                              │
                                         ┌────▼─────┐
                                         │ Supplier │
                                         └──────────┘
```

#### Node Types
- **Customer**: 1000+ customers with demographics, preferences, and segments
- **Product**: 700+ products across 6 categories with pricing and inventory
- **Category**: 25 categories with hierarchical relationships
- **Order**: 3050+ orders with purchase history
- **Review**: 1500+ reviews with ratings and sentiment
- **Supplier**: 50 suppliers with reliability scores

#### Relationship Types
- **PURCHASED**: Customer → Product (quantity, amount, date)
- **REVIEWED**: Customer → Product (rating, text, sentiment)
- **BELONGS_TO**: Product → Category
- **SUPPLIES**: Supplier → Product (reliability)
- **RECOMMENDS**: Customer → Product (ML-generated scores)

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────┐
│  8 Sequential GitHub Actions Workflows                  │
│  (Prerequisites → Infrastructure → Neo4j → ... → Tests)  │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Terraform IaC  │     │  Databricks     │
│  (UK South)     │     │  Neo4j Clusters │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ├───────────────────────┤
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Neo4j Aura     │◄────┤ Neo4j Connector │
│  UK South       │     │ 5.3.0 Spark 3.5 │
│  (E-commerce    │     └─────────────────┘
│   Graph DB)     │
└─────────────────┘
```

### E-commerce Data Flow
```
CSV Sample Data (1000+ customers, 700+ products)
         │
         ▼
Bronze Layer (Raw ingestion)
         │
         ▼
Silver Layer (Cleaning & validation)
         │
         ▼
Gold Layer (Business aggregations)
         │
         ▼
Graph Ready Layer (Neo4j format)
         │
         ▼
Neo4j Aura (Graph database)
         │
         ▼
Analytics (Customer 360, Recommendations, Supply Chain)
```

### Use Cases Implemented

1. **Customer 360 Analytics**
   - Complete purchase history
   - Preference analysis
   - Customer segmentation (RFM)
   - Lifetime value calculation

2. **Product Recommendation Engine**
   - Collaborative filtering
   - Category-based recommendations
   - Review-based suggestions
   - Trending products

3. **Supply Chain Optimization**
   - Supplier performance tracking
   - Inventory analysis
   - Reliability scoring
   - Product availability

4. **Graph Analytics**
   - Customer journey mapping
   - Cross-sell opportunities
   - Churn prediction patterns
   - Fraud detection (graph patterns)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## ⚙️ Configuration

### Terraform Variables
Configure in `terraform/terraform.tfvars` (copy from `terraform.tfvars.example`):

```hcl
# Example: terraform.tfvars
resource_group_name            = "rg-neo4j-dbx-dev"
location                       = "uksouth"
databricks_workspace_name      = "dbw-neo4j-dev"
databricks_sku                 = "premium"
create_databricks_workspace    = false  # Use existing workspace via DATABRICKS_HOST (default)
neo4j_tier                     = "professional"
neo4j_memory                   = "8GB"
catalog_name                   = "ecommerce_dev"
environment                    = "dev"
```

**Note:** By default, `create_databricks_workspace = false` and the pipeline uses an existing Databricks workspace specified by the `DATABRICKS_HOST` secret. Set to `true` only if you want Terraform to create a new Azure Databricks workspace.

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for complete configuration reference.

### Data Sources
Configure in `configs/data-sources.yml`:

```yaml
sources:
  - name: customers
    type: csv
    path: /mnt/data/customers.csv
    schema: customer_schema
  
  - name: orders
    type: csv
    path: /mnt/data/orders.csv
    schema: order_schema
```

### Cluster Configuration
Configure in `configs/cluster-configurations.yml`:

```yaml
dev:
  node_type_id: "Standard_DS3_v2"
  min_workers: 1
  max_workers: 3
  
prod:
  node_type_id: "Standard_DS4_v2"
  min_workers: 2
  max_workers: 10
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for all configuration options.

## 📊 Monitoring and Operations

### Application Insights
Monitor pipeline performance, errors, and custom metrics:
- Request rates and latencies
- Dependency tracking
- Exception tracking
- Custom events and metrics

### Alerting
Configure alerts as needed through Azure Monitor:
- Job failures
- Performance degradation
- Cost thresholds
- Secret expiration

### Logging
Centralized logging with Azure Monitor:
```bash
# View recent logs
az monitor activity-log list --resource-group <RG_NAME>

# Query specific logs
az monitor log-analytics query \
  --workspace <WORKSPACE_ID> \
  --analytics-query "traces | where message contains 'error'"
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Authentication Failures
```bash
# Verify Azure credentials
az login
az account show

# Test service principal
az login --service-principal \
  -u <CLIENT_ID> \
  -p <CLIENT_SECRET> \
  --tenant <TENANT_ID>
```

#### 2. Databricks Token Issues
```bash
# Generate new token
databricks tokens create --comment "Pipeline deployment"

# Update GitHub secret
gh secret set DATABRICKS_TOKEN
```

#### 3. Neo4j Connection Issues
```bash
# Verify credentials
curl -u <AURA_CLIENT_ID>:<AURA_CLIENT_SECRET> \
  https://api.neo4j.io/v1/instances
```

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed troubleshooting guide.

## ✅ Validation

### CI/CD Validation
All workflows include automated validation:
- Secret validation
- Infrastructure validation
- Notebook syntax checking
- Configuration validation

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and component overview
- [Deployment](docs/DEPLOYMENT.md) - Detailed deployment instructions
- [Secrets Management](docs/SECRETS_MANAGEMENT.md) - Comprehensive secrets guide
- [Configuration](docs/CONFIGURATION.md) - All configuration options
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/issues)
- **Discussions**: [GitHub Discussions](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/discussions)
- **Documentation**: [docs/](docs/)

## 🔄 Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and release notes.
