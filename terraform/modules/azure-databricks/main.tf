resource "azurerm_databricks_workspace" "main" {
  name                = var.workspace_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku

  tags = var.tags
}

# Create mount point configuration for storage
# Note: Actual mount creation happens in Databricks notebooks
data "azurerm_storage_account" "main" {
  name                = var.storage_account_name
  resource_group_name = var.resource_group_name
}

# Create access connector for Unity Catalog (optional, for future use)
resource "azurerm_databricks_access_connector" "main" {
  name                = "dac-${var.workspace_name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  
  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Grant storage access to Databricks managed identity
resource "azurerm_role_assignment" "databricks_storage" {
  scope                = data.azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.main.identity[0].principal_id
}
