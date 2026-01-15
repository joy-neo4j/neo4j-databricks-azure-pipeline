# Changelog

All notable changes to this project will be documented here.

## Upcoming Features

- GDS examples and feature engineering (e.g., PageRank) with write-back to Silver/Gold, positioning Neo4j in the middle of the Medallion Architecture.
- Large-scale loading best practices and integration with Neo4j Parallel Spark Loader for efficient, parallel relationship ingestion.
- A catalog of notebooks covering: write to Neo4j, read from Neo4j, and run graph algorithms in Databricks.

## [1.3.0] - 2026-01-15

### Documentation Improvements
- **README**: Streamlined from 769 to 92 lines with Quick Start focus
  - Added explanation for Quick Start (existing infra) vs Full Deployment (deploy workspace, Aura, validate)
  - Embedded Mermaid architecture diagram directly in README
  - Renamed "Detailed Docs" to "Detailed References" with descriptions
  - Added "Version History" section linking to CHANGELOG.md
  - Moved "Upcoming features" to CHANGELOG.md
- **PREREQUISITES.md**: Enhanced with comprehensive Prerequisite Permissions section
  - Azure Service Principal permissions (networking, storage, Key Vault, resource group, monitoring)
  - Databricks PAT user permissions (workspace admin, Unity Catalog, clusters, secret scopes)
  - Minimum required permissions summary and verification commands
- **ARCHITECTURE.md**: Refreshed to reflect current repository state
  - Embedded Mermaid diagram showing system flow
  - Added Deployment Architecture section documenting all current workflows
  - Updated data flow explanations
- **DEPLOYMENT.md**: Updated with actual workflow files
  - Core deployment workflows: 01-prerequisites-setup, 02-provision, 06-data-pipeline, 07-neo4j-integration-showcase
  - Operations workflows: compute-start, compute-stop, 10-stop-compute
  - Removed outdated workflow references
- **VALIDATION.md**: Created new validation procedures documentation
- **MONITORING.md**: Removed per consolidation feedback

### Workflow Enhancements
- **compute-start.yml**: New standalone workflow to start single Databricks cluster by ID with Neo4j connectivity validation
- **compute-stop.yml**: New standalone workflow to stop single Databricks cluster (with fallback: permanent-delete → delete → stop)
- **10-stop-compute.yml**: Enhanced "Start/Stop Compute" unified workflow
  - Added 4 actions: start-dbx-cluster, stop-dbx-clusters, start-aura, stop-aura
  - All actions require CONFIRM input and produce job summaries
  - Supports Neo4j Aura start/resume and stop/pause operations via OAuth2 API

### Other Changes
- Created `docs/diagrams/architecture.mmd` with Mermaid source for architecture diagram
- Consolidated compute management into unified workflows for better operational control

## [1.2.0] - 2026-01-06
- Integrate Databricks secrets setup into 06-data-pipeline workflow.
- Remove Terraform-managed Databricks secrets.
- Delete unused configs (monitoring-config.yml, secrets-config.yml).
- Rename cleanup to Stop Compute; implement Aura pause with tenant-aware fallback; skip when instance missing or already paused.
- Documentation cleanup (README, CONFIGURATION, DEPLOYMENT, TROUBLESHOOTING, Copilot instructions); add version history.

## [1.1.0] - 2026-01-05
- Switch workflows to Go-based Databricks CLI and env auth.
- Harden notebook failure signaling and workflow monitors.

## [1.0.0] - 2025-12-20
- Initial release of single-click Databricks + Neo4j pipeline deployer.
