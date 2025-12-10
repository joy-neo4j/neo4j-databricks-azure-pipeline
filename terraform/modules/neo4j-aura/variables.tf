variable "environment" {
  description = "Environment name"
  type        = string
}

variable "instance_name" {
  description = "Name of the Neo4j Aura instance"
  type        = string
}

variable "tier" {
  description = "Neo4j Aura tier"
  type        = string
  default     = "professional"
}

variable "memory" {
  description = "Memory size for Neo4j instance"
  type        = string
  default     = "8GB"
}

variable "region" {
  description = "Neo4j Aura region"
  type        = string
  default     = "eastus"
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
