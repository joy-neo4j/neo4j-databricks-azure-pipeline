# Configuration Guide

Complete configuration reference for the Neo4j-Databricks Azure Pipeline.

## Configuration Files

The pipeline uses the following YAML configuration files in the `configs/` directory:

### 1. Data Sources (`configs/data-sources.yml`)
Defines source data locations, schemas, and validation rules.

### 2. Cluster Configuration (`configs/cluster-configurations.yml`)
Specifies Databricks cluster settings including node types, worker counts, and Spark configurations.

### 3. Neo4j Connector Configuration (`configs/neo4j-connector-config.yml`)
Configuration for Neo4j Spark connector settings, including batch size, write mode, and connection parameters.

### Terraform Variables

#### Environment Configuration
Environment parameter has been removed. The pipeline operates in a single environment for simplicity and consistency.

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

## Data Source Configuration

### Data Sources (`configs/data-sources.yml`)

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

## Cluster Configuration

### Cluster Configuration (`configs/cluster-configurations.yml`)

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

## Neo4j Connector Configuration

### Neo4j Connector Configuration (`configs/neo4j-connector-config.yml`)

Configuration for Neo4j Spark connector settings, including batch size, write mode, and connection parameters.

## Single Environment Settings

Configure the pipeline via `terraform/terraform.tfvars`:

```hcl
# terraform/terraform.tfvars.example
resource_group_name     = "rg-neo4j-dbx"
location                = "uksouth"

storage_account_name    = null
storage_container_name  = "pipeline-data"

databricks_workspace_name = "dbw-neo4j"
databricks_sku            = "premium"

create_databricks_workspace = false

neo4j_region            = "uksouth"
neo4j_tier              = "professional"
neo4j_memory            = "8GB"

# Unity Catalog override (defaults to neo4j_pipeline if omitted)
catalog_name_override   = "neo4j_pipeline"
```

To customize for your environment:
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

**Note**: `terraform.tfvars` is git-ignored. Only non-secret defaults should be in this file. Secrets are provided via environment variables (TF_VAR_*) in the workflow.

## Workflow Configuration

No environment input is required. Workflows deploy to the single configured environment.

## Azure Resource Configuration

### Storage Account
- **Tier:** Standard (dev/staging), Premium (prod)
- **Replication:** LRS (dev), GRS (prod)
- **Hierarchical Namespace:** Enabled
- **Public Access:** Disabled

### Databricks Workspace
- **SKU:** Premium
- **Managed Resource Group:** Automatic
- **Public Network Access:** Enabled (dev/staging), disabled (prod)
- **Unity Catalog:** Enabled

## Best Practices

## Graph Ready Tables

The pipeline creates graph-ready tables in the `graph_ready` schema that are optimized for Neo4j loading:

### Core Tables
- **graph_ready.customer_nodes**: Customer entities with properties (name, email, age, etc.)
- **graph_ready.product_nodes**: Product entities with properties (name, description, price, etc.)
  - Properties may include `category` when available in silver.products
- **graph_ready.purchased_relationships**: Customer → Product PURCHASED relationships
  - Properties may include `purchase_date` and `amount` when available in silver.orders
- **graph_ready.reviewed_relationships**: Customer → Product REVIEWED relationships
  - Properties may include `review_date` and `rating` when available in silver.reviews

### Optional Supplier Tables
- **graph_ready.supplier_nodes**: Supplier entities (created only when silver.suppliers exists)
  - node_id = supplier_id
  - Properties include `name`, `country` when available
- **graph_ready.supplies_relationships**: Supplier → Product SUPPLIES relationships (created only when supplier data is available)
  - from_id = supplier_id, to_id = product_id

### Enrichment
The optional `graph_ready_enhancements.py` notebook enriches existing graph_ready tables with additional properties when matching silver data is present. Enrichments are:
- Schema-aware: only applied when source tables/columns exist
- Idempotent: can be run multiple times safely
- Non-breaking: existing functionality continues to work without running enhancements

### Naming Conventions
```
Resource Groups: rg-{project}
Storage: st{project}{random}
Databricks: dbw-{project}
```

### Tagging Strategy
```yaml
Environment: single
Project: neo4j-databricks-pipeline
ManagedBy: terraform
CostCenter: engineering
Owner: team-name
```

### Cost Optimization
- Use auto-pause where appropriate
- Right-size clusters
- Use spot instances where applicable
- Review costs monthly using Azure Cost Management

---

**Last Updated:** 2024-01-10
