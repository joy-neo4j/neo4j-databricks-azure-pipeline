variable "create_databricks_workspace" {
  description = "Create a new Azure Databricks workspace (true) or reuse existing via DATABRICKS_HOST (false)."
  type        = bool
  default     = false
}
