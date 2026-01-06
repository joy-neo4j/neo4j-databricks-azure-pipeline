# Changelog

## [1.2.0] - 2026-01-06
- Integrate Databricks secrets setup into 06-data-pipeline workflow.
- Remove Terraform-managed Databricks secrets.
- Delete unused configs (monitoring-config.yml, secrets-config.yml).
- Rename cleanup to Stop Compute; implement Aura pause endpoint with fail-on-error, but skip when instance missing or already paused.
- Comprehensive documentation cleanup.

## [1.1.0] - 2026-01-05
- Switch workflows to Go-based Databricks CLI and env auth.
- Harden notebook failure signaling and workflow monitors.

## [1.0.0] - 2025-12-20
- Initial release of single-click Databricks + Neo4j pipeline deployer.
