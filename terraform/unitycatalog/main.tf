provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}

resource "databricks_schema" "bronze"      { name = "bronze"      catalog_name = var.catalog_name comment = "Raw ingested data from source systems" }
resource "databricks_schema" "silver"      { name = "silver"      catalog_name = var.catalog_name comment = "Cleaned and validated e-commerce data" }
resource "databricks_schema" "gold"        { name = "gold"        catalog_name = var.catalog_name comment = "Business-level aggregated data" }
resource "databricks_schema" "graph_ready" { name = "graph_ready" catalog_name = var.catalog_name comment = "Data prepared for Neo4j graph loading" }
resource "databricks_schema" "customers"   { name = "customers"   catalog_name = var.catalog_name comment = "Customer-related data and analytics" }
resource "databricks_schema" "products"    { name = "products"    catalog_name = var.catalog_name comment = "Product catalog and category data" }
resource "databricks_schema" "orders"      { name = "orders"      catalog_name = var.catalog_name comment = "Order and transaction data" }
resource "databricks_schema" "analytics"   { name = "analytics"   catalog_name = var.catalog_name comment = "E-commerce analytics and ML features" }

output "catalog_name" {
  value = var.catalog_name
}
