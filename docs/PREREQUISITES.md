# Prerequisites

## Overview

This document outlines the permissions and requirements needed to deploy the Neo4j + Databricks pipeline.

## Required Tools

- Azure subscription with appropriate permissions
- GitHub account with Actions enabled
- Azure CLI (version 2.40+)
- Terraform (version 1.5+)
- Python 3.8+

## Azure Services

- **Existing Azure Databricks workspace** (Premium or Enterprise tier recommended)
  - Workspace URL should be provided via `DATABRICKS_HOST` secret
  - Set `create_databricks_workspace = false` in Terraform variables (default)
  - Alternatively, set `create_databricks_workspace = true` to create a new workspace
- Azure Resource Manager
- Azure Key Vault (for production secrets)
- Azure Monitor and Application Insights

## Neo4j Aura

- Neo4j Aura account (Professional or Enterprise tier)
- Aura API credentials

## Prerequisite Permissions

This section documents the specific roles and permissions required for deployment. Note that generic "Contributor" access is **not recommended** for production environments.

### Azure Service Principal Permissions

The Azure Service Principal used by GitHub Actions requires the following specific role assignments:

#### 1. Networking Permissions (for VNet/Subnet/NSG changes)
```bash
# Network Contributor role for networking resources
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Network Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>
```

#### 2. Storage Permissions (for Data Lake and Blob Storage)
```bash
# Storage Blob Data Contributor for storage account operations
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>/providers/Microsoft.Storage/storageAccounts/<STORAGE_ACCOUNT_NAME>

# Storage Account Contributor for storage account management
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Storage Account Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>/providers/Microsoft.Storage/storageAccounts/<STORAGE_ACCOUNT_NAME>
```

#### 3. Key Vault Permissions (for secrets management)
```bash
# Key Vault Administrator for managing secrets
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Key Vault Administrator" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>/providers/Microsoft.KeyVault/vaults/<KEY_VAULT_NAME>

# Alternatively, use Key Vault Secrets Officer for limited secret management
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Key Vault Secrets Officer" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>/providers/Microsoft.KeyVault/vaults/<KEY_VAULT_NAME>
```

#### 4. Resource Group Management
```bash
# Owner role at resource group level for full resource management
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Owner" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>
```

#### 5. Azure Databricks Workspace Access (if creating new workspace)
```bash
# Only required if create_databricks_workspace = true
# Databricks workspace requires Owner or Contributor at resource group level
# This is handled by the Owner role assignment above
```

#### 6. Monitoring and Logging
```bash
# Log Analytics Contributor for monitoring setup
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Log Analytics Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>

# Application Insights Component Contributor
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --role "Application Insights Component Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME>
```

### Databricks Personal Access Token (PAT) User Permissions

The Databricks PAT user requires the following permissions for Unity Catalog operations:

#### 1. Workspace Admin Role
The PAT user should have **Workspace Admin** privileges to manage clusters, jobs, and notebooks:

```bash
# Grant workspace admin via Databricks UI:
# Settings → Admin Console → Users → Select User → Role: Admin
```

#### 2. Unity Catalog Metastore Permissions

```sql
-- Grant CREATE on metastore (execute in Databricks SQL editor)
GRANT CREATE CATALOG ON METASTORE TO `<user_email>`;
GRANT CREATE SCHEMA ON CATALOG <catalog_name> TO `<user_email>`;
GRANT CREATE TABLE ON CATALOG <catalog_name> TO `<user_email>`;
```

#### 3. Catalog-Level Permissions
```sql
-- Grant full permissions on the catalog
GRANT ALL PRIVILEGES ON CATALOG <catalog_name> TO `<user_email>`;

-- Grant usage on catalog (minimum required)
GRANT USAGE ON CATALOG <catalog_name> TO `<user_email>`;
```

#### 4. Schema-Level Permissions
```sql
-- Grant permissions on specific schemas
GRANT CREATE, USAGE, SELECT, MODIFY ON SCHEMA <catalog_name>.bronze TO `<user_email>`;
GRANT CREATE, USAGE, SELECT, MODIFY ON SCHEMA <catalog_name>.silver TO `<user_email>`;
GRANT CREATE, USAGE, SELECT, MODIFY ON SCHEMA <catalog_name>.gold TO `<user_email>`;
GRANT CREATE, USAGE, SELECT, MODIFY ON SCHEMA <catalog_name>.graph_ready TO `<user_email>`;
```

#### 5. Storage Credential and External Location Permissions (for Unity Catalog)
```sql
-- Grant permissions to manage storage credentials
GRANT CREATE STORAGE CREDENTIAL ON METASTORE TO `<user_email>`;
GRANT CREATE EXTERNAL LOCATION ON METASTORE TO `<user_email>`;

-- Grant access to specific external location
GRANT READ FILES, WRITE FILES ON EXTERNAL LOCATION `<location_name>` TO `<user_email>`;
```

#### 6. Cluster Management Permissions
The PAT user needs **Can Manage** permission on clusters:

```bash
# Via Databricks UI:
# Compute → Select Cluster → Permissions → Add User → Permission: Can Manage
```

#### 7. Secret Scope Permissions
```bash
# Grant permissions on secret scopes (via Databricks CLI)
databricks secrets put-acl \
  --scope neo4j \
  --principal <user_email> \
  --permission MANAGE
```

### Minimum Required Permissions Summary

For a **production deployment with existing Databricks workspace** (`create_databricks_workspace = false`):

**Azure Service Principal:**
- Resource Group: `Owner` (for resource management)
- Storage: `Storage Blob Data Contributor` + `Storage Account Contributor`
- Key Vault: `Key Vault Secrets Officer` (minimum) or `Key Vault Administrator`
- Networking: `Network Contributor` (if using private endpoints)
- Monitoring: `Log Analytics Contributor` + `Application Insights Component Contributor`

**Databricks PAT User:**
- Workspace: `Admin` role
- Unity Catalog: `USAGE`, `CREATE`, `SELECT`, `MODIFY` on catalog and schemas
- Clusters: `Can Manage` permission
- Secret Scopes: `MANAGE` permission on secret scopes

### Verification Commands

```bash
# Verify Service Principal role assignments
az role assignment list \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --output table

# Verify Service Principal has access to Key Vault
az keyvault secret list \
  --vault-name <KEY_VAULT_NAME> \
  --query "[].name" \
  --output table

# Verify Databricks workspace access
databricks workspace list --profile <profile_name>

# Test Unity Catalog access (via Databricks SQL)
SHOW CATALOGS;
SHOW SCHEMAS IN CATALOG <catalog_name>;
```

## Quick Reference

### Azure Service Principal (Minimum Required)

- Resource Group: `Owner`
- Storage: `Storage Blob Data Contributor` + `Storage Account Contributor`
- Key Vault: `Key Vault Secrets Officer` or `Key Vault Administrator`
- Networking: `Network Contributor` (if using private endpoints)
- Monitoring: `Log Analytics Contributor` + `Application Insights Component Contributor`

### Databricks PAT User (Minimum Required)

- Workspace: `Admin` role
- Unity Catalog: `USAGE`, `CREATE`, `SELECT`, `MODIFY` on catalog and schemas
- Clusters: `Can Manage` permission
- Secret Scopes: `MANAGE` permission on secret scopes

## Verification

```bash
# Verify Service Principal role assignments
az role assignment list \
  --assignee <SERVICE_PRINCIPAL_APP_ID> \
  --output table

# Verify Databricks workspace access
databricks workspace list --profile <profile_name>

# Test Unity Catalog access (via Databricks SQL)
SHOW CATALOGS;
```

## See Also

- [Secrets Management](SECRETS_MANAGEMENT.md) - How to configure secrets
- [Deployment](DEPLOYMENT.md) - Deployment workflows
- [Configuration](CONFIGURATION.md) - Configuration options
