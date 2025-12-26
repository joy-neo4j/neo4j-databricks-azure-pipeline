
variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "workspace_name" {
  description = "Name of the Databricks workspace"
  type        = string
}

variable "sku" {
  description = "Databricks SKU"
  type        = string
  default     = "premium"
}

variable "storage_account_name" {
  description = "Name of the storage account"
  type        = string
}

variable "storage_container_name" {
  description = "Name of the storage container"
  type        = string
}

variable "enable_private_endpoint" {
  description = "Enable private endpoint"
  type        = bool
  default     = false
}

variable "vnet_address_space" {
  description = "Virtual network address space"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
