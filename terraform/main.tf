# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "Neo4j-Databricks-Pipeline"
  })
}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# Storage Account for Data
resource "azurerm_storage_account" "main" {
  name                     = coalesce(var.storage_account_name, "stneo4j${var.environment}${random_string.suffix.result}")
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  is_hns_enabled           = true
  
  tags = azurerm_resource_group.main.tags
}

resource "azurerm_storage_container" "data" {
  name                  = var.storage_container_name
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Key Vault for Secrets
resource "azurerm_key_vault" "main" {
  count                       = var.enable_key_vault ? 1 : 0
  name                        = coalesce(var.key_vault_name, "kv-neo4j-${var.environment}-${random_string.suffix.result}")
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  soft_delete_retention_days  = 7
  purge_protection_enabled    = var.environment == "prod"

  tags = azurerm_resource_group.main.tags
}

data "azurerm_client_config" "current" {}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  count               = var.enable_monitoring ? 1 : 0
  name                = coalesce(var.log_analytics_workspace_name, "log-neo4j-${var.environment}-${random_string.suffix.result}")
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "prod" ? 90 : 30

  tags = azurerm_resource_group.main.tags
}

# Application Insights
resource "azurerm_application_insights" "main" {
  count               = var.enable_monitoring ? 1 : 0
  name                = "appi-neo4j-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main[0].id
  application_type    = "other"

  tags = azurerm_resource_group.main.tags
}

# Azure Databricks Module
module "azure_databricks" {
  source = "./modules/azure-databricks"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_name      = coalesce(var.databricks_workspace_name, "dbw-neo4j-${var.environment}-${random_string.suffix.result}")
  sku                 = var.databricks_sku
  
  storage_account_name = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.data.name
  
  enable_private_endpoint = var.enable_private_endpoint
  vnet_address_space      = var.vnet_address_space
  
  tags = azurerm_resource_group.main.tags
}

# Neo4j Aura Module
module "neo4j_aura" {
  source = "./modules/neo4j-aura"

  environment        = var.environment
  tier               = var.neo4j_tier
  memory             = var.neo4j_memory
  region             = var.neo4j_region
  aura_client_id     = var.aura_client_id
  aura_client_secret = var.aura_client_secret
  
  instance_name = "neo4j-${var.environment}-${random_string.suffix.result}"
}

# Store Neo4j credentials in Key Vault
resource "azurerm_key_vault_secret" "neo4j_uri" {
  count        = var.enable_key_vault ? 1 : 0
  name         = "neo4j-uri-${var.environment}"
  value        = module.neo4j_aura.connection_uri
  key_vault_id = azurerm_key_vault.main[0].id
}

resource "azurerm_key_vault_secret" "neo4j_username" {
  count        = var.enable_key_vault ? 1 : 0
  name         = "neo4j-username-${var.environment}"
  value        = module.neo4j_aura.username
  key_vault_id = azurerm_key_vault.main[0].id
}

resource "azurerm_key_vault_secret" "neo4j_password" {
  count        = var.enable_key_vault ? 1 : 0
  name         = "neo4j-password-${var.environment}"
  value        = module.neo4j_aura.password
  key_vault_id = azurerm_key_vault.main[0].id
}

# Budget Alert
resource "azurerm_consumption_budget_resource_group" "main" {
  name              = "budget-neo4j-${var.environment}"
  resource_group_id = azurerm_resource_group.main.id

  amount     = var.budget_amount
  time_grain = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", timestamp())
  }

  notification {
    enabled   = true
    threshold = var.budget_alert_threshold
    operator  = "GreaterThanOrEqualTo"

    contact_emails = []
  }
}

############################################
# Databricks Resources
# NOTE: Databricks workspace is created by the azure_databricks module above.
#       The provider configuration uses the workspace URL from that module's output.
#       These resources (cluster, notebooks, jobs, etc.) are configured after
#       the workspace is created during the same Terraform apply.
############################################

############################################
# Databricks Cluster
############################################
resource "databricks_cluster" "neo4j_ecommerce" {
  cluster_name            = "neo4j-ecommerce-${var.environment}"
  spark_version           = "13.3.x-scala2.12"
  node_type_id            = "Standard_DS3_v2"
  autotermination_minutes = 120
  num_workers             = 2

  spark_conf = {
    "spark.sql.adaptive.enabled"             = "true"
    "spark.databricks.io.cache.enabled"      = "true"
    "spark.databricks.delta.preview.enabled" = "true"
  }

  custom_tags = {
    Environment = var.environment
    Purpose     = "Neo4j-Integration"
  }

  library {
    maven {
      coordinates = "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.0_for_spark_3.5"
      repo        = "https://repo1.maven.org/maven2/"
    }
  }
}

############################################
# Unity Catalog Schemas
# NOTE: Requires Unity Catalog (specified by var.catalog_name) to already exist
#       in the Databricks workspace. This Terraform configuration will create
#       schemas within the existing catalog.
############################################
resource "databricks_schema" "bronze" {
  name         = "bronze"
  catalog_name = var.catalog_name
  comment      = "Raw ingested data"
}

resource "databricks_schema" "silver" {
  name         = "silver"
  catalog_name = var.catalog_name
  comment      = "Validated data"
}

resource "databricks_schema" "gold" {
  name         = "gold"
  catalog_name = var.catalog_name
  comment      = "Aggregations"
}

resource "databricks_schema" "graph_ready" {
  name         = "graph_ready"
  catalog_name = var.catalog_name
  comment      = "Neo4j-formatted data"
}

resource "databricks_schema" "customers" {
  name         = "customers"
  catalog_name = var.catalog_name
  comment      = "Customer data"
}

resource "databricks_schema" "products" {
  name         = "products"
  catalog_name = var.catalog_name
  comment      = "Product data"
}

resource "databricks_schema" "orders" {
  name         = "orders"
  catalog_name = var.catalog_name
  comment      = "Order data"
}

resource "databricks_schema" "analytics" {
  name         = "analytics"
  catalog_name = var.catalog_name
  comment      = "Analytics"
}

############################################
# Upload Notebooks to Workspace
############################################
locals {
  notebook_base_path = "/Workspace/ecommerce-pipeline/notebooks"
}

resource "databricks_workspace_file" "csv_ingestion" {
  source    = "${path.module}/../databricks/notebooks/csv-ingestion.py"
  path      = "${local.notebook_base_path}/csv-ingestion"
  overwrite = true
}

resource "databricks_workspace_file" "data_validation" {
  source    = "${path.module}/../databricks/notebooks/data-validation.py"
  path      = "${local.notebook_base_path}/data-validation"
  overwrite = true
}

resource "databricks_workspace_file" "graph_transformation" {
  source    = "${path.module}/../databricks/notebooks/graph-transformation.py"
  path      = "${local.notebook_base_path}/graph-transformation"
  overwrite = true
}

resource "databricks_workspace_file" "neo4j_loading" {
  source    = "${path.module}/../databricks/notebooks/neo4j-loading.py"
  path      = "${local.notebook_base_path}/neo4j-loading"
  overwrite = true
}

resource "databricks_workspace_file" "customer_360_analytics" {
  source    = "${path.module}/../databricks/notebooks/customer-360-analytics.py"
  path      = "${local.notebook_base_path}/customer-360-analytics"
  overwrite = true
}

resource "databricks_workspace_file" "product_recommendations" {
  source    = "${path.module}/../databricks/notebooks/product-recommendations.py"
  path      = "${local.notebook_base_path}/product-recommendations"
  overwrite = true
}

############################################
# Key Vault-backed Secret Scope for Neo4j
############################################
resource "databricks_secret_scope" "neo4j" {
  count = var.enable_key_vault ? 1 : 0
  name  = "neo4j"

  keyvault_metadata {
    resource_id = azurerm_key_vault.main[0].id
    dns_name    = azurerm_key_vault.main[0].vault_uri
  }
}

############################################
# Jobs: ETL, Validation, Graph Transform, Neo4j Loading, Analytics
############################################
resource "databricks_job" "ecommerce_pipeline" {
  name = "Neo4j ETL Pipeline - ${var.environment}"

  task {
    task_key = "csv_ingestion"
    notebook_task {
      notebook_path   = databricks_workspace_file.csv_ingestion.path
      base_parameters = { environment = var.environment }
    }
    existing_cluster_id = databricks_cluster.neo4j_ecommerce.id
  }

  task {
    task_key = "data_validation"
    depends_on {
      task_key = "csv_ingestion"
    }
    notebook_task {
      notebook_path   = databricks_workspace_file.data_validation.path
      base_parameters = { environment = var.environment }
    }
    existing_cluster_id = databricks_cluster.neo4j_ecommerce.id
  }

  task {
    task_key = "graph_transformation"
    depends_on {
      task_key = "data_validation"
    }
    notebook_task {
      notebook_path   = databricks_workspace_file.graph_transformation.path
      base_parameters = { environment = var.environment }
    }
    existing_cluster_id = databricks_cluster.neo4j_ecommerce.id
  }

  task {
    task_key = "neo4j_loading"
    depends_on {
      task_key = "graph_transformation"
    }
    notebook_task {
      notebook_path   = databricks_workspace_file.neo4j_loading.path
      base_parameters = { environment = var.environment }
    }
    existing_cluster_id = databricks_cluster.neo4j_ecommerce.id
  }

  task {
    task_key = "customer_360_analytics"
    depends_on {
      task_key = "neo4j_loading"
    }
    notebook_task {
      notebook_path = databricks_workspace_file.customer_360_analytics.path
      base_parameters = {
        environment = var.environment
        catalog     = var.catalog_name
      }
    }
    existing_cluster_id = databricks_cluster.neo4j_ecommerce.id
  }

  task {
    task_key = "product_recommendations"
    depends_on {
      task_key = "customer_360_analytics"
    }
    notebook_task {
      notebook_path = databricks_workspace_file.product_recommendations.path
      base_parameters = {
        environment = var.environment
        catalog     = var.catalog_name
      }
    }
    existing_cluster_id = databricks_cluster.neo4j_ecommerce.id
  }

  max_concurrent_runs = 1
  timeout_seconds     = 7200
}

############################################
# Unity Catalog Grants (optional basic grants)
############################################
resource "databricks_grants" "catalog_grants" {
  catalog = var.catalog_name
  grant {
    principal  = "users"
    privileges = ["USE_CATALOG"]
  }
}

resource "databricks_grants" "schema_bronze_grants" {
  schema  = databricks_schema.bronze.name
  catalog = var.catalog_name
  grant {
    principal  = "users"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}

resource "databricks_grants" "schema_silver_grants" {
  schema  = databricks_schema.silver.name
  catalog = var.catalog_name
  grant {
    principal  = "users"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}

resource "databricks_grants" "schema_gold_grants" {
  schema  = databricks_schema.gold.name
  catalog = var.catalog_name
  grant {
    principal  = "users"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}

resource "databricks_grants" "schema_graph_ready_grants" {
  schema  = databricks_schema.graph_ready.name
  catalog = var.catalog_name
  grant {
    principal  = "users"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}
