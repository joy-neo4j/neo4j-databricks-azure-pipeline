provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}

resource "databricks_cluster" "neo4j_ecommerce" {
  cluster_name            = "neo4j-ecommerce-dev"
  spark_version           = "13.3.x-scala2.12"
  node_type_id            = "Standard_DS3_v2"
  autotermination_minutes = 120
  num_workers             = 2
  spark_conf = {
    "spark.sql.adaptive.enabled"             = "true"
    "spark.databricks.io.cache.enabled"      = "true"
    "spark.databricks.delta.preview.enabled" = "true"
  }
  custom_tags = {
    Environment = "dev"
    Purpose     = "Neo4j-Integration"
  }
  library {
    maven {
      coordinates = "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.0_for_spark_3.5"
      repo        = "https://repo1.maven.org/maven2/"
    }
  }
}

output "cluster_id" {
  value = databricks_cluster.neo4j_ecommerce.id
}
output "spark_version" {
  value = databricks_cluster.neo4j_ecommerce.spark_version
}
