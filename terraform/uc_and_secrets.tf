############################################
# Unity Catalog - Select First Available Catalog
############################################

# Fetch list of catalogs via Databricks API
data "http" "unity_catalog_list" {
  url = "${var.databricks_host}/api/2.1/unity-catalog/catalogs"
  request_headers = {
    Authorization = "Bearer ${var.databricks_token}"
  }
}

# Parse catalog list and select first or use override
locals {
  catalogs_response = jsondecode(data.http.unity_catalog_list.response_body)
  catalogs_list     = try(local.catalogs_response.catalogs, [])
  catalog_names     = [for c in local.catalogs_list : c.name]
  first_catalog     = length(local.catalog_names) > 0 ? local.catalog_names[0] : ""
  use_override      = var.catalog_name_override != "" && contains(local.catalog_names, var.catalog_name_override)
  resolved_catalog  = local.use_override ? var.catalog_name_override : local.first_catalog
}

# Fail-fast if no catalog found
resource "null_resource" "validate_catalog" {
  provisioner "local-exec" {
    command = <<-EOT
      if [ -z "${local.resolved_catalog}" ]; then
        echo "ERROR: No Unity Catalog found. Please create a catalog in Databricks first."
        exit 1
      fi
      echo "✓ Using Unity Catalog: ${local.resolved_catalog}"
    EOT
  }

  triggers = {
    catalog_name = local.resolved_catalog
  }
}

############################################
# Unity Catalog Schemas
############################################

resource "databricks_schema" "bronze" {
  depends_on   = [null_resource.validate_catalog]
  name         = "bronze"
  catalog_name = local.resolved_catalog
  comment      = "Raw ingested data"
}

resource "databricks_schema" "silver" {
  depends_on   = [null_resource.validate_catalog]
  name         = "silver"
  catalog_name = local.resolved_catalog
  comment      = "Validated data"
}

resource "databricks_schema" "gold" {
  depends_on   = [null_resource.validate_catalog]
  name         = "gold"
  catalog_name = local.resolved_catalog
  comment      = "Aggregations"
}

resource "databricks_schema" "graph_ready" {
  depends_on   = [null_resource.validate_catalog]
  name         = "graph_ready"
  catalog_name = local.resolved_catalog
  comment      = "Neo4j-formatted data"
}

# Removed Databricks Secret Scope and Secrets; these are now managed in GitHub Actions (06-data-pipeline)
