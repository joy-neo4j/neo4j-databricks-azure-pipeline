# Configuration Guide

Complete configuration reference for the Neo4j-Databricks Azure Pipeline.

## Configuration Files

### 1. Terraform Variables (`terraform/variables.tf`)

#### Environment Configuration
```hcl
variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Must be dev, staging, or prod"
  }
}
```

#### Azure Configuration
```hcl
variable "location" {
  description = "Azure region"
  default     = "eastus"
  # Options: eastus, westus2, centralus, northeurope, westeurope
}

variable "resource_group_name" {
  description = "Resource group name"
  # Pattern: rg-neo4j-databricks-{env}
}
```

#### Databricks Configuration
```hcl
variable "databricks_sku" {
  default = "premium"
  # Options: standard, premium, trial
}

variable "auto_pause_minutes" {
  default = 120
  # 0 = disabled, >0 = minutes until auto-pause
}
```

### 2. Data Sources (`configs/data-sources.yml`)

```yaml
sources:
  - name: source_name
    type: csv  # csv, json, parquet, delta
    path: /mnt/data/path/to/file
    schema:
      column_name: data_type  # integer, string, decimal, timestamp
    validation:
      required_columns: [col1, col2]
      unique_columns: [id]
      foreign_keys:
        - column: fk_column
          references: table.column
```

### 3. Cluster Configuration (`configs/cluster-configurations.yml`)

```yaml
environment_name:
  cluster_name: "name"
  spark_version: "13.3.x-scala2.12"
  node_type_id: "Standard_DS3_v2"
  num_workers: 2
  min_workers: 1
  max_workers: 10
  autotermination_minutes: 120
  spark_conf:
    "spark.config.key": "value"
  custom_tags:
    TagName: "TagValue"
```

### 4. Monitoring Configuration (`configs/monitoring-config.yml`)

```yaml
alerts:
  - name: alert_name
    severity: critical  # critical, warning, info
    condition:
      metric: metric_name
      operator: greater_than  # equals, greater_than, less_than
      threshold: value
      window_minutes: 15
    notification:
      - slack
      - email
    environments: [dev, staging, prod]
```

### 5. Secrets Configuration (`configs/secrets-config.yml`)

See [Secrets Management Guide](SECRETS_MANAGEMENT.md) for complete reference.

## Environment-Specific Settings

### Single Environment Configuration

The pipeline now uses a single environment configured via `terraform/terraform.tfvars`:

```hcl
# terraform/terraform.tfvars.example
resource_group_name     = "rg-neo4j-dbx-dev"
location                = "uksouth"

storage_account_name    = null
storage_container_name  = "pipeline-data"

databricks_workspace_name = "dbw-neo4j-dev"
databricks_sku            = "premium"

enable_key_vault        = true
key_vault_name          = null
enable_monitoring       = true

budget_amount           = 200
budget_alert_threshold  = 80

neo4j_region            = "uksouth"
neo4j_tier              = "professional"
neo4j_memory            = "8GB"

catalog_name            = "ecommerce_dev"

environment             = "dev"
```

To customize for your environment:
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

**Note**: `terraform.tfvars` is git-ignored. Only non-secret defaults should be in this file. Secrets are provided via environment variables (TF_VAR_*) in the workflow.

## Workflow Configuration

### GitHub Actions Inputs

```yaml
environment:
  description: 'Target environment'
  type: choice
  options: [dev, staging, prod]
  
action:
  description: 'Action to perform'
  type: choice
  options: [deploy, destroy, backup]
```

## Azure Resource Configuration

### Storage Account
- **Tier:** Standard (dev/staging), Premium (prod)
- **Replication:** LRS (dev), GRS (prod)
- **Hierarchical Namespace:** Enabled
- **Public Access:** Disabled

### Key Vault
- **SKU:** Standard
- **Soft Delete:** 7 days (dev/staging), enabled (prod)
- **Purge Protection:** Disabled (dev/staging), enabled (prod)
- **Access Policies:** Service principal, Databricks MI

### Databricks Workspace
- **SKU:** Premium
- **Managed Resource Group:** Automatic
- **Public Network Access:** Enabled (dev/staging), disabled (prod)
- **Unity Catalog:** Enabled

## Best Practices

### Naming Conventions
```
Resource Groups: rg-{project}-{env}
Storage: st{project}{env}{random}
Key Vault: kv-{project}-{env}-{random}
Databricks: dbw-{project}-{env}
```

### Tagging Strategy
```yaml
Environment: dev/staging/prod
Project: neo4j-databricks-pipeline
ManagedBy: terraform
CostCenter: engineering
Owner: team-name
```

### Cost Optimization
- Use auto-pause in non-prod
- Right-size clusters per environment
- Use spot instances where applicable
- Set budget alerts
- Review costs monthly

---

**Last Updated:** 2024-01-10
