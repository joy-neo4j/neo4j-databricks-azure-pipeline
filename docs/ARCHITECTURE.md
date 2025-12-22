# System Architecture

## Overview

The Neo4j-Databricks Azure Pipeline is a production-ready, cloud-native ETL solution that transforms relational data into graph format and loads it into Neo4j Aura. The architecture follows modern cloud best practices with multi-environment support, comprehensive monitoring, and automated deployment.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Actions                            │
│                    (Orchestration Layer)                         │
└────────┬────────────────────────────────────┬──────────────────┘
         │                                     │
         │ Terraform IaC                       │ Databricks Jobs
         │                                     │
         ▼                                     ▼
┌─────────────────┐                  ┌─────────────────────────┐
│  Azure          │                  │  Databricks             │
│  Infrastructure │                  │  Workspace              │
│                 │                  │                         │
│  - Resource Grp │                  │  - Notebooks            │
│  - Storage Acc  │◄────────────────►│  - Clusters             │
│  - Key Vault    │                  │  - Jobs                 │
│  - Monitor      │                  │  - Unity Catalog        │
└────────┬────────┘                  └──────────┬──────────────┘
         │                                       │
         │                                       │
         │                                       ▼
         │                            ┌──────────────────────┐
         │                            │  Data Processing     │
         │                            │                      │
         │                            │  Bronze → Silver     │
         │                            │  Silver → Gold       │
         │                            └──────────┬───────────┘
         │                                       │
         ▼                                       ▼
┌─────────────────┐                  ┌──────────────────────┐
│  Neo4j Aura     │◄─────────────────│  Graph               │
│  Graph Database │                  │  Transformation      │
│                 │                  │                      │
│  - Nodes        │                  │  - Nodes             │
│  - Relationships│                  │  - Relationships     │
│  - Constraints  │                  │  - Properties        │
└─────────────────┘                  └──────────────────────┘
```

## Component Architecture

### 1. Infrastructure Layer (Azure)

#### Resource Group
- Logical container for all Azure resources
- Environment-specific naming: `rg-neo4j-databricks-{env}`
- Tagging for cost tracking and organization

#### Storage Account
- Azure Data Lake Storage Gen2 (ADLS Gen2)
- Hierarchical namespace enabled
- Containers:
  - `pipeline-data`: Source CSV files
  - `bronze`: Raw ingested data
  - `silver`: Validated data
  - `gold`: Graph-ready data
  - `checkpoints`: Streaming checkpoints

#### Azure Databricks
- Premium tier for enhanced security
- Managed virtual network
- Unity Catalog integration
- Auto-scaling clusters
- Spot instance support for cost optimization

#### Azure Key Vault
- Centralized secrets management
- Soft-delete protection
- Access policies via managed identities
- Secrets:
  - Neo4j connection strings
  - Service principal credentials
  - API tokens

#### Azure Monitor (Optional)
- Log Analytics workspace (disabled by default, enable via `enable_monitoring = true`)
- Application Insights (disabled by default, enable via `enable_monitoring = true`)
- Custom metrics and alerts
- Query-based dashboards

### 2. Data Processing Layer (Databricks)

#### Bronze Layer (Raw Data)
**Purpose:** Store raw, unmodified data from sources

**Characteristics:**
- Append-only Delta tables
- Source file metadata
- Ingestion timestamps
- No transformations
- Schema validation on read

**Tables:**
- `neo4j_pipeline_{env}.bronze.customers`
- `neo4j_pipeline_{env}.bronze.products`
- `neo4j_pipeline_{env}.bronze.orders`

#### Silver Layer (Validated Data)
**Purpose:** Store cleaned, validated, and conformed data

**Characteristics:**
- Data quality checks applied
- Duplicate removal
- Type casting and validation
- Foreign key validation
- Business rule validation

**Tables:**
- `neo4j_pipeline_{env}.silver.customers`
- `neo4j_pipeline_{env}.silver.products`
- `neo4j_pipeline_{env}.silver.orders`

#### Gold Layer (Graph-Ready Data)
**Purpose:** Store business-level aggregates and graph structures

**Characteristics:**
- Graph node representations
- Graph relationship representations
- Denormalized for graph loading
- Enriched with metadata
- Optimized for Neo4j ingestion

**Tables:**
- `neo4j_pipeline_{env}.gold.nodes`
- `neo4j_pipeline_{env}.gold.relationships`

### 3. Graph Database Layer (Neo4j Aura)

#### Node Types
```cypher
// Customer nodes
(:Customer {
  id: integer,
  name: string,
  email: string,
  created_at: datetime
})

// Product nodes
(:Product {
  id: integer,
  name: string,
  category: string,
  price: decimal,
  created_at: datetime
})

// Order nodes
(:Order {
  id: integer,
  order_date: datetime,
  total_amount: decimal
})
```

#### Relationship Types
```cypher
// Customer placed an order
(c:Customer)-[:PLACED_ORDER {order_date: datetime}]->(o:Order)

// Order contains a product
(o:Order)-[:CONTAINS_PRODUCT {quantity: integer}]->(p:Product)
```

#### Constraints and Indexes
```cypher
// Uniqueness constraints
CREATE CONSTRAINT customer_id FOR (c:Customer) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT product_id FOR (p:Product) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT order_id FOR (o:Order) REQUIRE o.id IS UNIQUE;

// Performance indexes
CREATE INDEX customer_name FOR (c:Customer) ON (c.name);
CREATE INDEX product_name FOR (p:Product) ON (p.name);
CREATE INDEX order_date FOR (o:Order) ON (o.order_date);
```

### 4. Orchestration Layer (GitHub Actions)

#### Workflow Types

**1. Deploy Full Pipeline**
- Complete infrastructure deployment
- Databricks workspace setup
- Neo4j Aura provisioning
- Job and notebook deployment
- **Duration:** 15-20 minutes

**2. Deploy Infrastructure Only**
- Terraform-managed resources
- Azure services provisioning
- Network configuration
- **Duration:** 8-12 minutes

**3. Deploy Data Pipeline**
- Notebook updates
- Job configuration
- Cluster setup
- **Duration:** 5-8 minutes

**4. Scheduled ETL**
- Automated data processing
- Daily/hourly execution
- Monitoring and alerting
- **Duration:** Varies by data volume

**5. Environment Management**
- Promote between environments
- Rollback capabilities
- Backup and restore
- **Duration:** 5-10 minutes

**6. Resource Cleanup**
- Pause/stop clusters
- Delete temporary resources
- Cost optimization
- **Duration:** 2-5 minutes

## Data Flow

### ETL Pipeline Stages

```
1. INGESTION (Bronze)
   ├─ Read CSV from Azure Storage
   ├─ Apply schema
   ├─ Add metadata (timestamp, source file)
   └─ Write to Bronze Delta tables

2. VALIDATION (Silver)
   ├─ Check required columns
   ├─ Validate data types
   ├─ Check uniqueness constraints
   ├─ Validate foreign keys
   ├─ Calculate quality scores
   └─ Write to Silver Delta tables

3. TRANSFORMATION (Gold)
   ├─ Join related tables
   ├─ Create node representations
   ├─ Create relationship representations
   ├─ Add graph metrics (degree, etc.)
   └─ Write to Gold Delta tables

4. LOADING (Neo4j)
   ├─ Read from Gold tables
   ├─ Batch process nodes
   ├─ Create constraints/indexes
   ├─ Load nodes to Neo4j
   ├─ Load relationships to Neo4j
   └─ Verify data integrity
```

### Error Handling

Each stage includes:
- Try-catch blocks for graceful failure
- Detailed error logging
- Retry logic for transient errors
- Rollback capabilities
- Notification on failure

## Security Architecture

### Authentication & Authorization

**Azure Resources:**
- Service Principal with RBAC
- Managed Identities for Databricks
- Key Vault access policies
- Network security groups (optional)

**Databricks:**
- Personal Access Tokens (PAT)
- Unity Catalog permissions
- Cluster policies
- Workspace access controls

**Neo4j Aura:**
- API client credentials
- Database user credentials
- Connection string in Key Vault
- TLS/SSL encryption

### Secret Management

**Storage Hierarchy:**
1. GitHub Environment Secrets (highest priority)
2. GitHub Repository Secrets
3. Azure Key Vault
4. Databricks Secrets

**Secret Rotation:**
- Automated expiration warnings
- 90-day rotation for tokens
- 365-day rotation for service principals
- Audit logging

### Network Security

**Development:**
- Public endpoints
- IP whitelist (optional)
- Standard networking

**Production:**
- Private endpoints
- VNet integration
- No public internet access
- Azure Private Link

## Scalability & Performance

### Horizontal Scaling
- Databricks auto-scaling clusters
- Spot instances for cost optimization
- Worker node pools
- Dynamic resource allocation

### Vertical Scaling
- Node type selection per environment
- Driver node sizing
- Memory optimization
- CPU core allocation

### Performance Optimizations
- Delta Lake optimization
- Z-ordering for common queries
- Partition strategies
- Caching mechanisms
- Batch size tuning

## Monitoring & Observability

### Metrics
- Pipeline execution time
- Data volume processed
- Error rates
- Cost per execution
- Data quality scores

### Logs
- Structured JSON logging
- Centralized in Log Analytics (if enabled via `enable_monitoring = true`)
- Query-based analysis
- Retention policies by environment

### Alerts
- Job failures (critical)
- Performance degradation (warning)
- Cost thresholds (warning)
- Data quality issues (warning)
- Secret expiration (info)

### Dashboards
- Pipeline overview
- Cost analysis
- Data quality trends
- Performance metrics
- Error tracking

## Disaster Recovery

### Backup Strategy
- Delta table time travel (30 days)
- Notebook version control (Git)
- Infrastructure as Code (Terraform state)
- Configuration backups (daily)

### Recovery Procedures
1. Restore from Delta history
2. Redeploy infrastructure from Terraform
3. Restore notebooks from Git
4. Reconfigure secrets from backup
5. Verify data integrity

### RTO/RPO
- **Development:** RTO: 4 hours, RPO: 24 hours
- **Staging:** RTO: 2 hours, RPO: 12 hours
- **Production:** RTO: 1 hour, RPO: 1 hour

## Cost Optimization

### Strategies
1. **Auto-pause clusters** after inactivity
2. **Spot instances** for non-critical workloads
3. **Right-sizing** compute resources
4. **Scheduled execution** during off-peak hours
5. **Data lifecycle** policies (archival/deletion)

### Cost Breakdown (Monthly Estimates)

**Development Environment: $200-400**
- Databricks: $150-250
- Neo4j Aura: $50-100
- Azure Storage: $10-50

**Staging Environment: $400-600**
- Databricks: $250-400
- Neo4j Aura: $100-150
- Azure Storage: $50-100

**Production Environment: $800-1500**
- Databricks: $500-1000
- Neo4j Aura: $200-400
- Azure Storage: $100-200

## Deployment Strategy

### Environment Progression
```
Development → Staging → Production
```

### Approval Gates
- **Development:** No approval required
- **Staging:** 1 reviewer required
- **Production:** 2 reviewers required, manual approval

### Deployment Patterns
- Blue-green deployments (future)
- Canary releases (future)
- Feature flags (future)
- Rollback procedures

## Future Enhancements

### Planned Features
1. Real-time streaming ingestion
2. Advanced graph analytics
3. ML model integration
4. Multi-region deployment
5. GraphQL API layer
6. Web UI for monitoring
7. Self-service data onboarding

### Technical Debt
- Neo4j Terraform provider (when available)
- Enhanced error recovery
- Automated testing expansion
- Performance benchmarking suite

---

**Document Version:** 1.0.0  
**Last Updated:** 2024-01-10  
**Maintainer:** Platform Engineering Team
