# Azure Neo4j + Databricks Pipeline Deployer

[![Deploy Full Pipeline](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/actions/workflows/deploy-full-pipeline.yml/badge.svg)](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/actions/workflows/deploy-full-pipeline.yml)

A production-ready, single-click deployment solution for automated ETL pipelines using Azure Databricks and Neo4j Aura with comprehensive secrets management and multi-environment support.

## 🚀 Features

- **Single-Click Deployment**: Complete infrastructure and pipeline deployment in 15-20 minutes
- **Multi-Environment Support**: Dev, staging, and production configurations with approval gates
- **Enhanced Secrets Management**: GitHub secrets + Azure Key Vault integration with fallback mechanisms
- **Azure-Native Integration**: Resource Manager templates, Managed Identities, and Monitor integration
- **Cost Optimization**: Auto-pause, scheduling, and resource cleanup capabilities
- **Production Security**: Secret rotation, compliance checks, and security scanning
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
- Azure subscription with Owner or Contributor role
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
DATABRICKS_ACCOUNT_ID   # Account ID for workspace
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
```bash
az login
az ad sp create-for-rbac \
  --name "neo4j-databricks-pipeline" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID> \
  --sdk-auth
```

Copy the JSON output to the `AZURE_CREDENTIALS` secret.

### 4. Configure Environments

Create GitHub environments in your repository settings:
- **dev**: No approval required
- **staging**: 1 reviewer required
- **prod**: 2 reviewers required

### 5. Deploy

#### Option A: Full Pipeline (Recommended)
```bash
# Navigate to Actions → Deploy Full Pipeline → Run workflow
# Select environment: dev, staging, or prod
```

#### Option B: Manual Steps
```bash
# 1. Deploy infrastructure only
gh workflow run deploy-infrastructure.yml -f environment=dev

# 2. Deploy data pipeline
gh workflow run deploy-data-pipeline.yml -f environment=dev
```

### 6. Verify Deployment
```bash
# Check deployment status
gh run list --workflow=deploy-full-pipeline.yml

# View logs
gh run view <run-id> --log
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

### 1. Deploy Full Pipeline
**File**: `.github/workflows/deploy-full-pipeline.yml`
- **Duration**: 15-20 minutes
- **Includes**: Azure infrastructure, Neo4j Aura, Databricks workspace, jobs, and notebooks
- **Use Case**: Complete new environment setup

### 2. Deploy Infrastructure Only
**File**: `.github/workflows/deploy-infrastructure.yml`
- **Duration**: 8-12 minutes
- **Includes**: Azure resources and Neo4j Aura instance
- **Use Case**: Infrastructure-only updates

### 3. Deploy Data Pipeline
**File**: `.github/workflows/deploy-data-pipeline.yml`
- **Duration**: 5-8 minutes
- **Includes**: Databricks notebooks and job configurations
- **Use Case**: Code updates without infrastructure changes

### 4. Scheduled ETL
**File**: `.github/workflows/scheduled-etl.yml`
- **Schedule**: Configurable (default: daily at 2 AM UTC)
- **Includes**: Automated data processing with monitoring
- **Use Case**: Production data pipelines

### 5. Manage Environments
**File**: `.github/workflows/manage-environments.yml`
- **Actions**: Promote, rollback, backup
- **Use Case**: Environment management and promotion

### 6. Cleanup Resources
**File**: `.github/workflows/cleanup-resources.yml`
- **Actions**: Stop/pause/delete resources
- **Use Case**: Cost optimization and resource cleanup

## 🏗️ Architecture

### High-Level Architecture
```
┌─────────────────┐
│  GitHub Actions │
│   Orchestration │
└────────┬────────┘
         │
         ├─────────────────────────────────────────┐
         │                                         │
         ▼                                         ▼
┌──────────────────┐                    ┌──────────────────┐
│  Terraform IaC   │                    │ Databricks Jobs  │
│  Azure Resources │                    │   & Notebooks    │
└────────┬─────────┘                    └────────┬─────────┘
         │                                        │
         ├────────────────┬──────────────────────┤
         │                │                      │
         ▼                ▼                      ▼
┌─────────────┐  ┌─────────────────┐   ┌──────────────┐
│  Azure      │  │  Azure          │   │  Neo4j Aura  │
│  Key Vault  │  │  Databricks     │   │  Graph DB    │
└─────────────┘  └─────────────────┘   └──────────────┘
```

### Data Flow
```
CSV Data Sources → Databricks Ingestion → 
  Data Validation → Graph Transformation → 
  Neo4j Loading → Monitoring & Alerts
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## ⚙️ Configuration

### Environment Variables
Configure in `terraform/environments/{env}.tfvars`:

```hcl
# Example: dev.tfvars
environment         = "dev"
location            = "eastus"
resource_group_name = "rg-neo4j-databricks-dev"
databricks_sku      = "premium"
neo4j_tier          = "professional"
auto_pause_minutes  = 120
```

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
