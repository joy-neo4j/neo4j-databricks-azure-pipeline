# Note: This is a placeholder implementation
# Neo4j Aura doesn't have an official Terraform provider yet
# This module uses null_resource with local-exec to call Aura API
# In production, consider using the Neo4j Aura API directly via scripts

resource "random_password" "neo4j" {
  length  = 24
  special = true
}

# Placeholder for Neo4j Aura instance creation
# In practice, this would call the Aura API via a script
resource "null_resource" "neo4j_aura_instance" {
  provisioner "local-exec" {
    command = <<-EOT
      echo "Creating Neo4j Aura instance: ${var.instance_name}"
      echo "Tier: ${var.tier}, Memory: ${var.memory}, Region: ${var.region}"
      # In production, this would call:
      # curl -X POST https://api.neo4j.io/v1/instances \
      #   -u $AURA_CLIENT_ID:$AURA_CLIENT_SECRET \
      #   -H "Content-Type: application/json" \
      #   -d '{"name":"${var.instance_name}","memory":"${var.memory}","region":"${var.region}"}'
    EOT
    
    environment = {
      AURA_CLIENT_ID     = var.aura_client_id
      AURA_CLIENT_SECRET = var.aura_client_secret
    }
  }

  triggers = {
    instance_name = var.instance_name
    tier          = var.tier
    memory        = var.memory
    region        = var.region
  }
}

# Store instance metadata
locals {
  # Placeholder values - in production, these would come from Aura API response
  instance_id     = "neo4j-${var.environment}-${substr(md5(var.instance_name), 0, 8)}"
  connection_uri  = "neo4j+s://${local.instance_id}.databases.neo4j.io"
  username        = "neo4j"
  password        = random_password.neo4j.result
}
