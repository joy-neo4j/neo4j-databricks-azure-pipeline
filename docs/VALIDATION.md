# Validation

## Overview

This document describes how to validate your Neo4j + Databricks pipeline deployment and ensure all components are working correctly.

## CI/CD Validation

All workflows include automated validation:
- Secret validation
- Infrastructure validation
- Notebook syntax checking
- Configuration validation

## Manual Validation Steps

### 1. Verify Infrastructure Deployment

```bash
# Check deployment status
gh run list --workflow=02-provision.yml

# View logs
gh run view <run-id> --log

# Check Terraform outputs
cd terraform
terraform output
```

### 2. Verify Databricks Workspace

```bash
# List workspaces
databricks workspace list

# Verify notebooks are uploaded
databricks workspace list /Shared/neo4j-pipeline
```

### 3. Verify Unity Catalog

Connect to your Databricks workspace and run:

```sql
-- Show available catalogs
SHOW CATALOGS;

-- Verify schemas exist
SHOW SCHEMAS IN CATALOG <your_catalog_name>;

-- Expected schemas: bronze, silver, gold, graph_ready
```

### 4. Verify Neo4j Connectivity

Use the validation snippet from the Compute Start workflow or run manually:

```python
import os
from neo4j import GraphDatabase

uri = os.environ.get('NEO4J_URI')
user = os.environ.get('NEO4J_USERNAME')
pwd = os.environ.get('NEO4J_PASSWORD')

driver = GraphDatabase.driver(uri, auth=(user, pwd))
with driver.session() as session:
    result = session.run('RETURN 1 as ok')
    assert result.single()['ok'] == 1
    print('✅ Neo4j connectivity OK')
driver.close()
```

### 5. Verify Data Pipeline

After running the showcase workflow or manual pipeline execution:

```sql
-- In Databricks, verify tables exist
USE CATALOG <your_catalog>;

-- Check Bronze tables
SHOW TABLES IN bronze;

-- Check Silver tables
SHOW TABLES IN silver;

-- Check graph_ready tables
SHOW TABLES IN graph_ready;

-- Verify data counts
SELECT COUNT(*) FROM bronze.customers;
SELECT COUNT(*) FROM silver.customers;
```

### 6. Verify Neo4j Graph Data

Connect to Neo4j Browser or use Cypher:

```cypher
// Count nodes
MATCH (n) RETURN labels(n) as label, count(*) as count ORDER BY count DESC;

// Count relationships
MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY count DESC;

// Verify sample data
MATCH (c:Customer)-[:PURCHASED]->(p:Product)
RETURN c.customer_id, p.product_name
LIMIT 10;
```

## Start/Stop Workflow Validation

### Compute Start Workflow

The `Compute Start` workflow validates:
- Databricks authentication
- Cluster start capability
- Neo4j connectivity

Check the workflow summary for validation results.

### Compute Stop Workflow

The `Compute Stop` workflow validates:
- Databricks authentication
- Cluster stop capability

Check the workflow summary for results.

## Troubleshooting

If validation fails, see:
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Secrets Management](SECRETS_MANAGEMENT.md)
- [Deployment Guide](DEPLOYMENT.md)

## Automated Tests

Run automated tests if available:

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/
```

## Monitoring

For ongoing validation and monitoring:
- Azure Monitor dashboards
- Application Insights logs
- Databricks job run monitoring
