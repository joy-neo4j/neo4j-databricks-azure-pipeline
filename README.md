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

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Secrets Configuration](#secrets-configuration)
- [Deployment Workflows](#deployment-workflows)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Monitoring and Operations](#monitoring-and-operations)
- [Troubleshooting](#troubleshooting)
- [Cost Management](#cost-management)
- [Contributing](#contributing)

## 🔧 Prerequisites

### Required Tools
- Azure subscription with appropriate access (see [Prerequisite Permissions](#prerequisite-permissions) for specific roles)
- GitHub account with Actions enabled
- Azure CLI (version 2.40+)
- Terraform (version 1.5+)
- Python 3.8+

### Azure Services
- Azure Databricks (Premium or Enterprise tier recommended)
- Azure Resource Manager
- Azure Key Vault (for production secrets)
- Azure Monitor and Application Insights

### Neo4j Aura
- Neo4j Aura account (Professional or Enterprise tier)
- Aura API credentials

### Prerequisite Permissions

#### Azure Service Principal Roles

**IMPORTANT**: Do NOT use the generic "Contributor" role. Instead, assign specific roles as follows:

1. **User Access Administrator** (to allow creation of role assignments):
   ```bash
   az role assignment create \
     --assignee <APP_ID_OR_OBJECT_ID> \
     --role "User Access Administrator" \
     --scope /subscriptions/<SUB_ID>
   ```

2. **Network Contributor** (if Terraform manages VNets/Subnets/NSGs):
   ```bash
   az role assignment create \
     --assignee <APP_ID_OR_OBJECT_ID> \
     --role "Network Contributor" \
     --scope /subscriptions/<SUB_ID>/resourceGroups/<RG_NAME>
   ```

3. **Storage Blob Data Contributor** (data plane on the Storage Account used for state/data):
   ```bash
   az role assignment create \
     --assignee <APP_ID_OR_OBJECT_ID> \
     --role "Storage Blob Data Contributor" \
     --scope $(az storage account show -n <SA_NAME> -g <RG_NAME> --query id -o tsv)
   ```

4. **Key Vault** (choose ONE model):
   
   **Option A - Access Policy model:**
   ```bash
   az keyvault set-policy \
     -n <KV_NAME> \
     --spn <APP_ID> \
     --secret-permissions get list set delete purge recover
   ```
   
   **Option B - RBAC model** (with `enable_rbac_authorization = true` on the vault):
   ```bash
   az role assignment create \
     --assignee <OBJECT_ID> \
     --role "Key Vault Secrets Officer" \
     --scope $(az keyvault show -n <KV_NAME> --query id -o tsv)
   ```

#### Databricks PAT User Permissions

The Databricks Personal Access Token (PAT) user must have:

1. **Metastore Admin** at the Databricks Account level
2. **Catalog-level privileges** to create schemas/manage grants (e.g., ALL_PRIVILEGES)

**Example: Grant catalog privileges using Databricks CLI**

Ensure `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are set:
```bash
databricks unity-catalog privileges set \
  --json '{
    "securable_type":"catalog",
    "securable_name":"ecommerce_dev",
    "changes":[{
      "principal":"<user@domain>",
      "add":["ALL_PRIVILEGES"]
    }]
  }'
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
DATABRICKS_TOKEN        # Personal access token

# Neo4j Aura
AURA_CLIENT_ID          # Aura API client ID
AURA_CLIENT_SECRET      # Aura API client secret
```

#### Optional Secrets
```bash
SLACK_WEBHOOK_URL       # Slack notifications
NOTIFICATION_EMAIL      # Email notifications
```

See [SECRETS_MANAGEMENT.md](docs/SECRETS_MANAGEMENT.md) for detailed setup instructions.

### 3. Create Azure Service Principal

Create a service principal and assign specific roles (see [Prerequisite Permissions](#prerequisite-permissions) above):

```bash
az login

# Create service principal (without role assignment)
az ad sp create-for-rbac \
  --name "neo4j-databricks-pipeline" \
  --skip-assignment \
  --sdk-auth
```

Copy the JSON output to the `AZURE_CREDENTIALS` secret, then assign the specific roles listed in the [Prerequisite Permissions](#prerequisite-permissions) section (DO NOT use generic "Contributor").

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

# 2. Validate data pipeline notebooks
gh workflow run 06-data-pipeline.yml

# 3. Run end-to-end showcase (optional)
gh workflow run 07-neo4j-integration-showcase.yml
```

**Note**: The new `02-provision.yml` workflow consolidates the previous workflows 02-05 into a single Terraform deployment.

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
  - Unity Catalog schemas (bronze, silver, gold, graph_ready, etc.)
  - Databricks notebooks uploaded to workspace
  - Databricks jobs (ETL pipeline with 6 tasks)
  - Key Vault-backed secret scope for Neo4j credentials
  - Unity Catalog grants for users
- **Use Case**: Complete infrastructure and pipeline deployment in one workflow
- **Note**: Consolidates the functionality of previous workflows 02-05

#### 3. Data Pipeline Validation
**File**: `.github/workflows/06-data-pipeline.yml`
- **Duration**: 2-3 minutes
- **Validates**: Notebook syntax and Python compilation
- **Use Case**: Syntax validation for notebooks (deployment handled by Terraform)

#### 4. Neo4j Integration Showcase (Optional)
**File**: `.github/workflows/07-neo4j-integration-showcase.yml`
- **Duration**: 10-15 minutes
- **Executes**: Complete e-commerce pipeline from ingestion to Neo4j
- **Use Case**: End-to-end pipeline validation and showcase

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
resource_group_name       = "rg-neo4j-dbx-dev"
location                  = "uksouth"
databricks_workspace_name = "dbw-neo4j-dev"
databricks_sku            = "premium"
neo4j_tier                = "professional"
neo4j_memory              = "8GB"
catalog_name              = "ecommerce_dev"
environment               = "dev"
```

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
Configure alerts in `configs/monitoring-config.yml`:
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
# Test Aura connection
python scripts/configure-neo4j-connection.py --test

# Verify credentials
curl -u <AURA_CLIENT_ID>:<AURA_CLIENT_SECRET> \
  https://api.neo4j.io/v1/instances
```

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed troubleshooting guide.

## 💰 Cost Management

### Cost Optimization Features
- **Auto-pause**: Databricks clusters pause after inactivity
- **Scheduled jobs**: Run during off-peak hours
- **Resource tagging**: Track costs by environment
- **Cleanup workflows**: Remove unused resources

### Estimated Costs (Monthly)
- **Dev Environment**: $200-400
  - Databricks: $150-250
  - Neo4j Aura: $50-100
  - Azure Storage: $10-50

- **Production Environment**: $800-1500
  - Databricks: $500-1000
  - Neo4j Aura: $200-400
  - Azure Storage/Services: $100-200

### Cost Monitoring
```bash
# View current costs
az consumption usage list --start-date 2024-01-01

# Set budget alerts
az consumption budget create \
  --budget-name neo4j-pipeline \
  --amount 1000 \
  --time-grain Monthly
```

## 🧪 Testing

### Run Tests Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run pipeline validation
python scripts/validate-prerequisites.py
```

### CI/CD Testing
All workflows include automated testing:
- Secret validation
- Infrastructure validation
- Notebook syntax checking
- Integration tests

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

## 🙏 Acknowledgments

- Azure Databricks team for comprehensive API documentation
- Neo4j Aura team for graph database excellence
- Community contributors and testers

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/issues)
- **Discussions**: [GitHub Discussions](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/discussions)
- **Documentation**: [docs/](docs/)

## 🔄 Version History

- **v1.0.0** (2024-01): Initial release with complete deployment automation
  - Multi-environment support
  - Enhanced secrets management
  - Production-ready workflows
  - Comprehensive documentation

---

**Built with ❤️ for the Azure and Neo4j communities**
