# Unity Catalog Variables
variable "catalog_name_override" {
  description = "Optional: Override catalog name (if empty, will use first available catalog)"
  type        = string
  default     = ""
}

# Neo4j Connection Variables for Databricks Secrets
variable "neo4j_uri" {
  description = "Neo4j connection URI (e.g., neo4j+s://xxx.databases.neo4j.io)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "neo4j_username" {
  description = "Neo4j username"
  type        = string
  sensitive   = true
  default     = ""
}

variable "neo4j_password" {
  description = "Neo4j password"
  type        = string
  sensitive   = true
  default     = ""
}
