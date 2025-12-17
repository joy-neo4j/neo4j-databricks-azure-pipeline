variable "databricks_host" {
  type        = string
  description = "Databricks workspace URL"
}
variable "databricks_token" {
  type        = string
  description = "Databricks PAT"
}
variable "catalog_name" {
  type        = string
  default     = "ecommerce_dev"
  description = "Existing Unity Catalog name (must exist)"
}
