# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags = merge(var.tags, {
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

data "azurerm_client_config" "current" {}

# Azure Databricks Module
module "azure_databricks" {
  count  = var.create_databricks_workspace ? 1 : 0
  source = "./modules/azure-databricks"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_name      = coalesce(var.databricks_workspace_name, "dbw-neo4j-${var.environment}-${random_string.suffix.result}")
  sku                 = var.databricks_sku

  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.data.name

  enable_private_endpoint = var.enable_private_endpoint
  vnet_address_space      = var.vnet_address_space

  tags = azurerm_resource_group.main.tags
}

# Neo4j Aura Instance (direct implementation - provider approach)
# Note: neo4jaura provider is not yet available in Terraform registry
# This implementation uses null_resource with Aura API as a provider-like pattern at root

resource "random_password" "neo4j" {
  length  = 24
  special = true
}

# Neo4j Aura instance provisioning via API
resource "null_resource" "neo4j_aura_instance" {
  provisioner "local-exec" {
    command = <<-EOT
      echo "Creating Neo4j Aura instance: neo4j-ecommerce-${var.environment}"
      echo "Tier: ${var.neo4j_tier}, Memory: ${var.neo4j_memory}, Region: ${var.neo4j_region}"
      # In production, this would call:
      # curl -X POST https://api.neo4j.io/v1/instances \
      #   -u $AURA_CLIENT_ID:$AURA_CLIENT_SECRET \
      #   -H "Content-Type: application/json" \
      #   -d '{"name":"neo4j-ecommerce-${var.environment}","memory":"${var.neo4j_memory}","region":"${var.neo4j_region}","cloud_provider":"azure","type":"${var.neo4j_tier}","version":"5"}'
    EOT

    environment = {
      AURA_CLIENT_ID     = var.aura_client_id
      AURA_CLIENT_SECRET = var.aura_client_secret
    }
  }

  triggers = {
    instance_name = "neo4j-ecommerce-${var.environment}"
    tier          = var.neo4j_tier
    memory        = var.neo4j_memory
    region        = var.neo4j_region
  }
}

# Store instance metadata (placeholders until actual API integration)
locals {
  neo4j_instance_id    = "neo4j-${var.environment}-${substr(md5("neo4j-ecommerce-${var.environment}"), 0, 8)}"
  neo4j_connection_uri = "neo4j+s://${local.neo4j_instance_id}.databases.neo4j.io"
  neo4j_username       = "neo4j"
  neo4j_password       = random_password.neo4j.result
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
    jar = "dbfs:${databricks_dbfs_file.neo4j_spark_connector_jar.path}"
  }
}

############################################
# Unity Catalog Schemas
# NOTE: Requires Unity Catalog (specified by local.resolved_catalog) to already exist
#       in the Databricks workspace. This Terraform configuration will create
#       schemas within the existing catalog.
#       Schema resources are now defined in uc_and_secrets.tf
############################################

resource "databricks_schema" "customers" {
  name         = "customers"
  catalog_name = local.resolved_catalog
  comment      = "Customer data"
}

resource "databricks_schema" "products" {
  name         = "products"
  catalog_name = local.resolved_catalog
  comment      = "Product data"
}

resource "databricks_schema" "orders" {
  name         = "orders"
  catalog_name = local.resolved_catalog
  comment      = "Order data"
}

resource "databricks_schema" "analytics" {
  name         = "analytics"
  catalog_name = local.resolved_catalog
  comment      = "Analytics"
}

############################################
# Upload Notebooks to Workspace
############################################
locals {
  notebook_base_path = "/Workspace/ecommerce-pipeline/notebooks"
}

resource "databricks_workspace_file" "csv_ingestion" {
  source = "${path.module}/../databricks/notebooks/csv-ingestion.py"
  path   = "${local.notebook_base_path}/csv-ingestion"
}

resource "databricks_workspace_file" "data_validation" {
  source = "${path.module}/../databricks/notebooks/data-validation.py"
  path   = "${local.notebook_base_path}/data-validation"
}

resource "databricks_workspace_file" "graph_transformation" {
  source = "${path.module}/../databricks/notebooks/graph-transformation.py"
  path   = "${local.notebook_base_path}/graph-transformation"
}

resource "databricks_workspace_file" "neo4j_loading" {
  source = "${path.module}/../databricks/notebooks/neo4j-loading.py"
  path   = "${local.notebook_base_path}/neo4j-loading"
}

resource "databricks_workspace_file" "customer_360_analytics" {
  source = "${path.module}/../databricks/notebooks/customer-360-analytics.py"
  path   = "${local.notebook_base_path}/customer-360-analytics"
}

resource "databricks_workspace_file" "product_recommendations" {
  source = "${path.module}/../databricks/notebooks/product-recommendations.py"
  path   = "${local.notebook_base_path}/product-recommendations"
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
        catalog     = local.resolved_catalog
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
        catalog     = local.resolved_catalog
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
  catalog = local.resolved_catalog
  grant {
    principal  = "users"
    privileges = ["USE_CATALOG"]
  }
}

resource "databricks_grants" "schema_bronze_grants" {
  schema  = databricks_schema.bronze.name
  catalog = local.resolved_catalog
  grant {
    principal  = "users"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}

resource "databricks_grants" "schema_silver_grants" {
  schema  = databricks_schema.silver.name
  catalog = local.resolved_catalog
  grant {
    principal  = "users"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}

resource "databricks_grants" "schema_gold_grants" {
  schema  = databricks_schema.gold.name
  catalog = local.resolved_catalog
  grant {
    principal  = "users"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}

resource "databricks_grants" "schema_graph_ready_grants" {
  schema  = databricks_schema.graph_ready.name
  catalog = local.resolved_catalog
  grant {
    principal  = "users"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}
