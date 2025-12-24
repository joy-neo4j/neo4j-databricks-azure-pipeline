############################################
# Sample Data Upload to Azure Storage
# Uploads local sample-data/ content into the provisioned container
############################################

locals {
  sample_data_dir   = "${path.module}/../sample-data"
  sample_data_files = fileset(local.sample_data_dir, "**")
}

resource "azurerm_storage_blob" "sample_data" {
  for_each               = toset(local.sample_data_files)
  name                   = "sample-data/${each.value}"
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.data.name
  type                   = "Block"
  source                 = "${local.sample_data_dir}/${each.value}"

  content_type = lookup({
    "csv"     = "text/csv",
    "json"    = "application/json",
    "parquet" = "application/octet-stream"
  }, element(reverse(split(".", each.value)), 0), "application/octet-stream")
}
