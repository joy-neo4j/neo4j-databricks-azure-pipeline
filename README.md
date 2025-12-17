# Neo4j + Databricks E-commerce Analytics Pipeline

[![Azure Infrastructure](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/actions/workflows/02-azure-infrastructure.yml/badge.svg)](https://github.com/joy-neo4j/neo4j-databricks-azure-pipeline/actions/workflows/02-azure-infrastructure.yml)

A production-ready, single-click deployment solution for **e-commerce analytics** using Azure Databricks and Neo4j Aura. Features comprehensive graph-based customer journey analysis, product recommendations, and supply chain optimization with Neo4j Spark Connector 5.3.0 optimized for UK South region.

## 🚀 Features

### E-commerce Analytics Capabilities
- **Customer 360 View**: Complete customer journey analysis with purchase history and preferences
- **Product Recommendations**: Collaborative filtering and graph-based recommendation engine
- **Supply Chain Analytics**: Supplier performance tracking and inventory optimization
- **Neo4j Graph Integration**: High-performance batch loading with Spark Connector 5.3.0
- **UK South Optimization**: Regional deployment for data residency and GDPR compliance

### Infrastructure & Deployment
- **8 Sequential Workflows**: Automated deployment from prerequisites to validation
- **Single-Click Deployment**: Complete infrastructure and pipeline deployment in 15-20 minutes
- **Multi-Environment Support**: Dev, staging, and production configurations with approval gates
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

### 4. Deploy

#### Automated Deployment via GitHub Actions

Navigate to the Actions tab in your repository and run workflows in sequence:
```bash
# 1. Deploy Azure infrastructure
gh workflow run 02-azure-infrastructure.yml

# 2. Deploy Neo4j Aura
gh workflow run 03-neo4j-aura-setup.yml

# 3. Configure Databricks
gh workflow run 04-databricks-configuration.yml

# 4. Setup Unity Catalog
gh workflow run 05-unity-catalog-setup.yml

# 5. Deploy data pipeline
gh workflow run 06-data-pipeline.yml
```

### 5. Verify Deployment
```bash
# Check deployment status
gh run list --workflow=02-azure-infrastructure.yml

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

### Sequential E-commerce Pipeline Workflows

#### 1. Prerequisites Setup
**File**: `.github/workflows/01-prerequisites-setup.yml`
- **Duration**: 2-3 minutes
- **Validates**: Azure credentials, Databricks token, Neo4j Aura credentials, Neo4j Spark Connector 5.3.0
- **Use Case**: Pre-deployment validation and compatibility checks

#### 2. Azure Infrastructure Deployment
**File**: `.github/workflows/02-azure-infrastructure.yml`
- **Duration**: 8-12 minutes
- **Deploys**: UK South Azure resources, storage, Key Vault, networking for Neo4j
- **Use Case**: Infrastructure foundation with regional optimization

#### 3. Neo4j Aura Setup
**File**: `.github/workflows/03-neo4j-aura-setup.yml`
- **Duration**: 5-8 minutes
- **Creates**: Performance-optimized Neo4j Aura instance in UK South
- **Configures**: E-commerce indexes, constraints, and optimization settings
- **Use Case**: Graph database setup for e-commerce workloads

#### 4. Databricks Configuration
**File**: `.github/workflows/04-databricks-configuration.yml`
- **Duration**: 5-7 minutes
- **Configures**: Neo4j-dedicated clusters with Spark Connector 5.3.0
- **Installs**: Libraries, init scripts, and performance tuning
- **Use Case**: Databricks cluster optimization for Neo4j integration

#### 5. Unity Catalog Setup
**File**: `.github/workflows/05-unity-catalog-setup.yml`
- **Duration**: 3-5 minutes
- **Creates**: E-commerce catalogs and schemas (bronze, silver, gold, graph_ready)
- **Configures**: Tables optimized for traditional clusters
- **Use Case**: Data governance and organization

#### 6. Data Pipeline
**File**: `.github/workflows/06-data-pipeline.yml`
- **Duration**: 5-8 minutes
- **Deploys**: E-commerce ETL notebooks, Neo4j loading jobs, analytics notebooks
- **Creates**: Scheduled jobs for data processing
- **Use Case**: Complete data pipeline deployment

#### 7. Neo4j Integration Showcase
**File**: `.github/workflows/07-neo4j-integration-showcase.yml`
- **Duration**: 10-15 minutes
- **Executes**: Complete e-commerce pipeline from ingestion to Neo4j
- **Use Case**: End-to-end pipeline validation and showcase

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
