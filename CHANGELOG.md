# Changelog

All notable changes to this project will be documented here.

## Upcoming Features

- GDS examples and feature engineering (e.g., PageRank) with write-back to Silver/Gold, positioning Neo4j in the middle of the Medallion Architecture.
- Large-scale loading best practices and integration with Neo4j Parallel Spark Loader for efficient, parallel relationship ingestion.
- A catalog of notebooks covering: write to Neo4j, read from Neo4j, and run graph algorithms in Databricks.

## [1.3.0] - 2026-01-15
- Streamline README from 769 to 92 lines with Quick Start focus and embedded Mermaid architecture diagram.
- Add explanation for Quick Start (existing infra) vs Full Deployment (deploy workspace, Aura, validate).
- Enhance PREREQUISITES.md with comprehensive permission requirements and verification commands.
- Refresh ARCHITECTURE.md and DEPLOYMENT.md to reflect current workflows and remove outdated references.
- Create VALIDATION.md for validation procedures; remove MONITORING.md.
- Add new standalone workflows: compute-start.yml (start cluster + Neo4j validation), compute-stop.yml (stop cluster).
- Enhance 10-stop-compute.yml with unified start/stop actions for Databricks clusters and Neo4j Aura.
- Add Version History section in README linking to CHANGELOG.md.

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
