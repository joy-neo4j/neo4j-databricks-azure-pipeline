output "instance_id" {
  description = "ID of the Neo4j Aura instance"
  value       = local.instance_id
}

output "connection_uri" {
  description = "Connection URI for Neo4j Aura"
  value       = local.connection_uri
  sensitive   = true
}

output "username" {
  description = "Username for Neo4j Aura"
  value       = local.username
  sensitive   = true
}

output "password" {
  description = "Password for Neo4j Aura"
  value       = local.password
  sensitive   = true
}
