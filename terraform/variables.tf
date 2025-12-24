variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "uksouth"
}

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Databricks Configuration
variable "databricks_sku" {
  description = "Databricks SKU (standard, premium, trial)"
  type        = string
  default     = "premium"
  validation {
    condition     = contains(["standard", "premium", "trial"], var.databricks_sku)
    error_message = "Databricks SKU must be standard, premium, or trial."
  }
}

variable "databricks_host" {
  description = "Databricks workspace URL"
  type        = string
}

variable "databricks_token" {
  description = "Databricks personal access token"
  type        = string
  sensitive   = true
}

variable "databricks_workspace_name" {
  description = "Name of the Databricks workspace"
  type        = string
  default     = ""
}

# Neo4j Configuration
variable "neo4j_tier" {
  description = "Neo4j Aura tier (professional, enterprise)"
  type        = string
  default     = "professional"
}

variable "neo4j_memory" {
  description = "Neo4j memory size in GB"
  type        = string
  default     = "8GB"
}

variable "neo4j_region" {
  description = "Neo4j Aura region"
  type        = string
  default     = "uksouth"
}

variable "aura_client_id" {
  description = "Neo4j Aura API client ID"
  type        = string
  sensitive   = true
}

variable "aura_client_secret" {
  description = "Neo4j Aura API client secret"
  type        = string
  sensitive   = true
}

# Storage Configuration
variable "storage_account_name" {
  description = "Name of the storage account for data"
  type        = string
  default     = ""
}

variable "storage_container_name" {
  description = "Name of the storage container for data"
  type        = string
  default     = "pipeline-data"
}

# Auto-pause Configuration
variable "auto_pause_minutes" {
  description = "Minutes of inactivity before auto-pause (0 to disable)"
  type        = number
  default     = 120
}

# Network Configuration
variable "enable_private_endpoint" {
  description = "Enable private endpoint for Databricks"
  type        = bool
  default     = false
}

variable "vnet_address_space" {
  description = "Address space for virtual network"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

# Unity Catalog Configuration
# Note: Unity Catalog selection is now handled automatically via HTTP API
# See terraform/uc_and_secrets.tf and terraform/variables.uc.tf

