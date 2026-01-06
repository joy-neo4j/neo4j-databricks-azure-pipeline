# GitHub Secrets Management Guide

## Overview

This guide provides comprehensive instructions for managing GitHub secrets in the Neo4j-Databricks pipeline deployment. GitHub repository secrets are synced to Databricks secret scope "pipeline-secrets" by the `06-data-pipeline.yml` workflow using the Go-based Databricks CLI.

## Table of Contents

- [Secret Types](#secret-types)
- [Required Secrets](#required-secrets)
- [Databricks Secrets Synchronization](#databricks-secrets-synchronization)
- [Setup Instructions](#setup-instructions)
- [Secret Validation](#secret-validation)
- [Secret Rotation](#secret-rotation)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Secret Types

### Repository Secrets
Shared across all environments and workflows. Suitable for:
- Development credentials
- Non-production resources
- Shared API keys

### Environment Secrets
Not required. The pipeline operates in a single environment. Use repository secrets for all deployments.

## Databricks Secrets Synchronization

The `06-data-pipeline.yml` workflow automatically synchronizes GitHub repository secrets to Databricks:

- **Scope:** `pipeline-secrets` (created automatically if it doesn't exist)
- **Method:** Go-based Databricks CLI with environment variable authentication
- **Keys synchronized:**
  - `aura-client-id` (from `AURA_CLIENT_ID` GitHub secret)
  - `aura-client-secret` (from `AURA_CLIENT_SECRET` GitHub secret)
  - `neo4j-uri` (from `NEO4J_URI` GitHub secret)
  - `neo4j-username` (from `NEO4J_USERNAME` GitHub secret)
  - `neo4j-password` (from `NEO4J_PASSWORD` GitHub secret)

**Note:** This approach replaces Terraform-managed Databricks secrets. The workflow handles secret scope creation and population idempotently. Run the `06-data-pipeline.yml` workflow after updating any Neo4j or Aura credentials in GitHub secrets.

## Required Secrets

### Azure Authentication

#### `AZURE_CREDENTIALS`
**Type:** JSON  
**Required:** Yes  
**Description:** Azure service principal credentials for resource deployment

**Format:**
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "your-client-secret",
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

**How to create:**
```bash
az login
az ad sp create-for-rbac \
  --name "neo4j-databricks-pipeline" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID> \
  --sdk-auth
```

#### `AZURE_SUBSCRIPTION_ID`
**Type:** UUID  
**Required:** Yes  
**Description:** Azure subscription ID

**How to get:**
```bash
az account show --query id -o tsv
```

#### `AZURE_TENANT_ID`
**Type:** UUID  
**Required:** Yes  
**Description:** Azure Active Directory tenant ID

**How to get:**
```bash
az account show --query tenantId -o tsv
```

### Databricks Configuration

#### `DATABRICKS_HOST`
**Type:** URL  
**Required:** Yes  
**Description:** Databricks workspace URL

**Format:** `https://<workspace-id>.azuredatabricks.net`

**How to get:**
- After workspace creation via Terraform
- From Azure Portal → Databricks workspace → URL

#### `DATABRICKS_TOKEN`
**Type:** String  
**Required:** Yes  
**Description:** Databricks personal access token
**Rotation:** Every 90 days

**How to create:**
1. Login to Databricks workspace
2. Click User Settings → Access Tokens
3. Click "Generate New Token"
4. Set comment: "GitHub Actions Pipeline"
5. Set lifetime: 90 days
6. Copy token (starts with `dapi`)

#### `DATABRICKS_ACCOUNT_ID`
**Type:** UUID  
**Required:** Yes  
**Description:** Databricks account ID for workspace creation

**How to get:**
- From Databricks Account Console
- URL: `https://accounts.azuredatabricks.net`

### Neo4j Aura Configuration

#### `AURA_CLIENT_ID`
**Type:** UUID  
**Required:** Yes  
**Description:** Neo4j Aura API client ID

**How to create:**
1. Login to Neo4j Aura Console
2. Navigate to Account Settings → API Keys
3. Click "Create API Key"
4. Name: "GitHub Actions Pipeline"
5. Copy Client ID

#### `AURA_CLIENT_SECRET`
**Type:** String  
**Required:** Yes  
**Description:** Neo4j Aura API client secret
**Rotation:** Every 90 days

**How to create:**
- Created at the same time as Client ID
- **Important:** Save immediately, cannot be retrieved later

#### `NEO4J_URI`
**Type:** URL  
**Required:** Yes  
**Description:** Neo4j database connection URI (Aura instance or self-hosted)

**Format:** `neo4j+s://xxxxx.databases.neo4j.io` or `bolt://hostname:7687`

**How to get:**
- From Neo4j Aura Console → Instance Details → Connection URI
- For self-hosted: Your Neo4j server URL

#### `NEO4J_USERNAME`
**Type:** String  
**Required:** Yes  
**Description:** Neo4j database username

**Default:** `neo4j` (for most installations)

**How to get:**
- Aura: From instance creation or password reset
- Self-hosted: Configured during Neo4j installation

#### `NEO4J_PASSWORD`
**Type:** String  
**Required:** Yes  
**Description:** Neo4j database password
**Rotation:** Every 90 days recommended

**How to get:**
- Aura: Set during instance creation or via password reset
- Self-hosted: Configured during Neo4j installation or via `neo4j-admin set-initial-password`

#### `AURA_INSTANCE_ID` (Optional)
**Type:** String  
**Required:** No (only for stop-aura workflow action)  
**Description:** Neo4j Aura instance ID for suspend/resume operations

**How to get:**
- From Neo4j Aura Console → Instance Details → Instance ID
- Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

## Setup Instructions

### Method 1: Manual Setup (via GitHub UI)

1. **Navigate to Repository Secrets:**
   ```
   Repository → Settings → Secrets and variables → Actions → New repository secret
   ```

2. **Add Each Required Secret:**
   - Click "New repository secret"
   - Enter secret name exactly as specified
   - Paste secret value
   - Click "Add secret"

3. **Verify Secrets:**
   - All required secrets should appear in the list
   - Environment-specific secrets in each environment

### Method 2: Automated Setup (via CLI)

1. **Install GitHub CLI:**
   ```bash
   # macOS
   brew install gh
   
   # Linux
   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
   ```

2. **Authenticate:**
   ```bash
   gh auth login
   ```

3. **Set secrets via CLI:**
   ```bash
   # Azure credentials
   gh secret set AZURE_CREDENTIALS < azure-credentials.json
   gh secret set AZURE_SUBSCRIPTION_ID --body "$(az account show --query id -o tsv)"
   gh secret set AZURE_TENANT_ID --body "$(az account show --query tenantId -o tsv)"
   
   # Databricks credentials
   gh secret set DATABRICKS_HOST --body "YOUR_WORKSPACE_URL"
   gh secret set DATABRICKS_TOKEN --body "YOUR_TOKEN"
   
   # Neo4j credentials
   gh secret set NEO4J_URI --body "YOUR_NEO4J_URI"
   gh secret set NEO4J_USERNAME --body "neo4j"
   gh secret set NEO4J_PASSWORD --body "YOUR_PASSWORD"
   
   # Aura credentials
   gh secret set AURA_CLIENT_ID --body "YOUR_CLIENT_ID"
   gh secret set AURA_CLIENT_SECRET --body "YOUR_CLIENT_SECRET"
   
   # Optional: Aura instance ID for stop-aura workflow action
   gh secret set AURA_INSTANCE_ID --body "YOUR_INSTANCE_ID"
   ```

4. **Run 06-data-pipeline workflow to sync secrets to Databricks:**
   ```bash
   gh workflow run 06-data-pipeline.yml
   ```

## Secret Synchronization to Databricks

After setting GitHub secrets, the `06-data-pipeline.yml` workflow automatically:
1. Creates the `pipeline-secrets` scope in Databricks (if it doesn't exist)
2. Populates the following keys from GitHub secrets:
   - `aura-client-id`
   - `aura-client-secret`
   - `neo4j-uri`
   - `neo4j-username`
   - `neo4j-password`

**When to re-run:** After updating any Neo4j or Aura credentials in GitHub secrets, re-run the `06-data-pipeline.yml` workflow to synchronize changes to Databricks.

## Secret Validation

### Automatic Validation
All workflows include a validation step that checks:
- Secret existence
- Secret format (UUID, JSON, URL)
- Secret content structure
- Token validity (prefix check)

### Manual Validation
```bash
# Verify secret existence via GitHub CLI
gh secret list
```

### Validation Rules

| Secret | Validation |
|--------|-----------|
| AZURE_CREDENTIALS | Valid JSON with required fields |
| AZURE_SUBSCRIPTION_ID | Valid UUID format |
| AZURE_TENANT_ID | Valid UUID format |
| DATABRICKS_TOKEN | Starts with `dapi`, length > 30 |
| AURA_CLIENT_ID | Valid UUID format |
| AURA_CLIENT_SECRET | Length > 20 characters |

## Secret Rotation

### Recommended Rotation Schedule

| Secret | Frequency | Priority |
|--------|-----------|----------|
| DATABRICKS_TOKEN | 90 days | High |
| AURA_CLIENT_SECRET | 90 days | High |
| AZURE_CREDENTIALS | 365 days | Medium |

### Rotation Process

1. **Create New Secret:**
   ```bash
   # Example: New Databricks token
   databricks tokens create --comment "Rotation $(date +%Y-%m-%d)"
   ```

2. **Update GitHub Secret:**
   ```bash
   gh secret set DATABRICKS_TOKEN --repo your-org/your-repo
   # Paste new token when prompted
   ```

3. **Verify New Secret:**
   ```bash
   gh secret list
   ```

4. **Revoke Old Secret:**
   ```bash
   # Example: Revoke old Databricks token
   databricks tokens delete --token-id <old-token-id>
   ```

### Automated Rotation Reminders
The monitoring configuration includes alerts for secrets expiring within 14 days.

## Best Practices

### Security
1. **Never commit secrets to code**
2. **Enable secret scanning in repository settings**
3. **Rotate secrets regularly**
4. **Use minimal required permissions**
5. **Audit secret access logs**

### Organization
1. **Use consistent naming conventions**
2. **Document all secrets in this guide**
3. **Maintain secret inventory**
4. **Use secret prefixes for clarity**
5. **Group related secrets**

### Access Control
1. **Limit secret access to necessary personnel**
2. **Require approvals on protected branches**
3. **Enable audit logging**
4. **Review access regularly**

## Troubleshooting

### Secret Not Found Error
```
Error: Required secret AZURE_CREDENTIALS not found
```

**Solutions:**
1. Verify secret name (case-sensitive)
2. Check secret is in correct scope (repository vs environment)
3. Validate workflow permissions
4. Check typos in secret reference

### Invalid Secret Format
```
Error: Secret validation failed for AZURE_CREDENTIALS
```

**Solutions:**
1. Verify JSON format is valid
2. Check all required fields are present
3. Remove extra whitespace
4. Ensure quotes are properly escaped

### Authentication Failed
```
Error: Azure authentication failed
```

**Solutions:**
1. Verify service principal is valid
2. Check subscription ID matches
3. Ensure service principal has required permissions
4. Verify secret hasn't expired

### Token Expired
```
Error: Databricks token expired or invalid
```

**Solutions:**
1. Generate new token in Databricks
2. Update GitHub secret
3. Verify token starts with `dapi`
4. Check token hasn't been revoked

## Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Azure Service Principal Guide](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal)
- [Databricks Token Management](https://docs.databricks.com/dev-tools/auth.html#personal-access-tokens)
- [Neo4j Aura API Documentation](https://neo4j.com/docs/aura/platform/api/)

## Support

For issues related to secrets management:
1. Check this documentation first
2. Run validation script
3. Review workflow logs
4. Open GitHub issue with details
5. Contact repository maintainers

---

**Last Updated:** 2024-01-10  
**Version:** 1.0.0
