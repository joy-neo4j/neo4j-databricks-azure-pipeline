# Resource Group
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.main.location
}

# Storage Account
output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_account_primary_connection_string" {
  description = "Primary connection string for the storage account"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "storage_container_name" {
  description = "Name of the storage container"
  value       = azurerm_storage_container.data.name
}

# Databricks
output "databricks_workspace_id" {
  description = "ID of the Databricks workspace"
  value       = var.create_databricks_workspace ? module.azure_databricks[0].workspace_id : null
}

output "databricks_workspace_url" {
  description = "URL of the Databricks workspace"
  value       = var.create_databricks_workspace ? module.azure_databricks[0].workspace_url : var.databricks_host
}

output "databricks_workspace_name" {
  description = "Name of the Databricks workspace"
  value       = var.create_databricks_workspace ? module.azure_databricks[0].workspace_name : null
}

# Neo4j Aura
output "neo4j_instance_id" {
  description = "ID of the Neo4j Aura instance"
  value       = local.neo4j_instance_id
}

output "neo4j_connection_uri" {
  description = "Connection URI for Neo4j Aura"
  value       = local.neo4j_connection_uri
  sensitive   = true
}

output "neo4j_username" {
  description = "Username for Neo4j Aura"
  value       = local.neo4j_username
  sensitive   = true
}

output "neo4j_password" {
  description = "Password for Neo4j Aura"
  value       = local.neo4j_password
  sensitive   = true
}

# Deployment Info
output "deployment_info" {
  description = "Summary of deployment information"
  value = {
    environment          = "single"
    resource_group       = azurerm_resource_group.main.name
    location             = azurerm_resource_group.main.location
    databricks_workspace = var.create_databricks_workspace ? module.azure_databricks[0].workspace_name : "existing-workspace"
    databricks_url       = var.create_databricks_workspace ? module.azure_databricks[0].workspace_url : var.databricks_host
    neo4j_instance       = local.neo4j_instance_id
    storage_account      = azurerm_storage_account.main.name
  }
}
