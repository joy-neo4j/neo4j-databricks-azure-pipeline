provider "neo4jaura" {
  client_id     = var.aura_client_id
  client_secret = var.aura_client_secret
}

resource "neo4jaura_instance" "auradb" {
  name           = "neo4j-ecommerce-dev"
  region         = var.region
  cloud_provider = "azure"
  type           = var.instance_type
  memory         = var.memory
  version        = "5"
}
