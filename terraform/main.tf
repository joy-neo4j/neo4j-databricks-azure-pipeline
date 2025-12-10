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
