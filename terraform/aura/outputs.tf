output "connection_uri" {
  value       = neo4jaura_instance.auradb.connection_uri
  description = "Bolt+s connection URI"
}

output "username" {
  value       = neo4jaura_instance.auradb.username
  description = "Default username"
}

output "password" {
  value       = neo4jaura_instance.auradb.password
  description = "Initial password"
}
