variable "aura_client_id" {
  type        = string
  description = "Neo4j Aura client ID"
}

variable "aura_client_secret" {
  type        = string
  description = "Neo4j Aura client secret"
}

variable "region" {
  type        = string
  default     = "uksouth"
  description = "Aura region (Azure UK South)"
}

variable "memory" {
  type        = string
  default     = "8GB"
  description = "AuraDB instance memory size"
}

variable "instance_type" {
  type        = string
  default     = "professional"
  description = "AuraDB instance type (e.g., professional)"
}
