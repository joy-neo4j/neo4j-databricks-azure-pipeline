############################################
# Neo4j Constraints Notebook Upload
############################################

resource "databricks_workspace_file" "neo4j_constraints" {
  source = "${path.module}/../databricks/notebooks/neo4j-constraints.py"
  path   = "/Shared/neo4j-pipeline/neo4j-constraints"
}

############################################
# Neo4j Constraints Job (Manual execution)
############################################

resource "databricks_job" "neo4j_constraints" {
  name = "Neo4j Constraints Setup - ${var.environment}"

  task {
    task_key = "neo4j_constraints"
    notebook_task {
      notebook_path = databricks_workspace_file.neo4j_constraints.path
    }

    new_cluster {
      spark_version           = "13.3.x-scala2.12"
      node_type_id            = "Standard_DS3_v2"
      num_workers             = 1
      autotermination_minutes = 30

      spark_conf = {
        "spark.databricks.delta.preview.enabled" = "true"
      }
    }
  }

  max_concurrent_runs = 1
  timeout_seconds     = 3600

  # Optional: Add dependency on secret scope to ensure secrets exist
  depends_on = [databricks_secret_scope.pipeline_secrets]
}
