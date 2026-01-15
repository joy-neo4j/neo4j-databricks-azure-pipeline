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

## Detailed Permission Requirements

For comprehensive permission requirements including:
- Azure Service Principal permissions
- Databricks PAT user permissions
- Unity Catalog permissions
- Verification commands

Please see below for a quick reference summary.

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
