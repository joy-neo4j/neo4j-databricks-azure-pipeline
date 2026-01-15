# Changelog

All notable changes to this project will be documented here.

## Upcoming Features (Secondary Scope)

- GDS examples and feature engineering (e.g., PageRank) with write-back to Silver/Gold, positioning Neo4j in the middle of the Medallion Architecture.
- Large-scale loading best practices and integration with Neo4j Parallel Spark Loader for efficient, parallel relationship ingestion.
- A catalog of notebooks covering: write to Neo4j, read from Neo4j, and run graph algorithms in Databricks.

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
