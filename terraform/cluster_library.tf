############################################
# Neo4j Spark Connector JAR - Upload to DBFS
############################################

resource "databricks_dbfs_file" "neo4j_spark_connector_jar" {
  source = "${path.module}/../build/neo4j-spark-connector-5.3.10-s_2.12.jar"
  path   = "/FileStore/jars/neo4j-spark-connector-5.3.10-s_2.12.jar"
}

############################################
# Attach JAR to Databricks Cluster
# This is handled via library block in the cluster resource
# See databricks_cluster.neo4j_ecommerce in main.tf
############################################
