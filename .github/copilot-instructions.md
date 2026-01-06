# Copilot Instructions: Neo4j + Databricks Azure Pipeline

## Scope & Big Picture
- **Purpose:** Production-ready ETL/analytics pipeline that ingests CSVs, validates/transforms into Bronze/Silver/Gold layers, converts to graph structures, and loads into Neo4j Aura.
- **Layers & Flow:** [databricks/notebooks](databricks/notebooks) run in order: `csv-ingestion.py` → `data-validation.py` → `graph-transformation.py` → `neo4j-loading.py`. This sequence is mirrored by jobs defined in Terraform.
- **Orchestration:** GitHub Actions workflows in [.github/workflows](.github/workflows) drive end-to-end deploys. IaC resides in [terraform](terraform), runtime configs in [configs](configs), and ops docs in [docs](docs).

## Developer Workflows
- **CI/CD deploys:** Trigger sequential workflows with `gh workflow run` per [README](README.md#L60). Key workflow: `02-provision.yml` in [.github/workflows](.github/workflows).
- **Tests:** `pytest tests/unit/` and `pytest tests/integration/`. Config shape expectations in tests.

## Configuration Conventions
- **Terraform:** Single-environment setup; avoid per-env variables in workflows and notebooks. Use consistent resource naming/tagging per [docs/CONFIGURATION.md](docs/CONFIGURATION.md#L1).
- **Runtime configs:**
  - Data sources in [configs/data-sources.yml](configs/data-sources.yml) with `schema`, `validation` blocks.
  - Clusters per env in [configs/cluster-configurations.yml](configs/cluster-configurations.yml) (node types, workers, autotermination).
  - Neo4j connector settings in [configs/neo4j-connector-config.yml](configs/neo4j-connector-config.yml).
- **Databricks job params:** Notebooks run without `environment` parameters; preserve task ordering and dependencies.

## Secrets & Auth
- **Required secrets:** `AZURE_CREDENTIALS`, `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `DATABRICKS_TOKEN`, `AURA_CLIENT_ID`, `AURA_CLIENT_SECRET`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` (see [docs/SECRETS_MANAGEMENT.md](docs/SECRETS_MANAGEMENT.md#L1)).
- **Optional secrets:** `AURA_INSTANCE_ID` (for stop-aura workflow), `AURA_TENANT_ID` (for tenant-aware Aura API fallback).
- **Fallback pattern:** Prefer environment-scoped (e.g., `PROD_AZURE_CREDENTIALS`) then repository secrets; workflows use this format consistently.
- **Secrets management:** GitHub Actions workflow `06-data-pipeline.yml` creates Databricks secret scope "pipeline-secrets" and populates Neo4j/Aura credentials (aura-client-id, aura-client-secret, neo4j-uri, neo4j-username, neo4j-password) from GitHub secrets using the Go-based Databricks CLI. Terraform does not manage Databricks secrets.

## Patterns To Follow
- **Notebook order & idempotence:** Maintain the 4-stage notebook chain; don't bypass validation before graph transforms.
- **Delta layers:**
  - Bronze: raw append-only tables.
  - Silver: cleaned/validated tables.
  - Graph Ready: graph-ready nodes/relationships for Neo4j loading.
- **Terraform changes:** Keep variable validations intact and update env `*.tfvars.example` when adding new inputs; do not hardcode per-env values in `main.tf`.
- **Resource naming & tags:** Use conventions in [docs/CONFIGURATION.md](docs/CONFIGURATION.md#L100) for RG/Storage/KeyVault/Databricks; keep `ManagedBy=terraform`, `Environment`, `Project` tags.

## Integration Points
- **Databricks ↔ Neo4j:** Neo4j Spark connector (5.3.10) JAR uploaded to DBFS and attached to cluster via Terraform. Credentials stored in Databricks secret scope "pipeline-secrets" (managed by `06-data-pipeline.yml`).
- **GitHub Actions:** Workflow `02-provision.yml` downloads Neo4j JAR, then runs Terraform to provision infrastructure and configure Unity Catalog. Workflow `06-data-pipeline.yml` handles Databricks secrets setup.
- **Unity Catalog:** Terraform automatically selects first available catalog or uses override. Schemas (bronze, silver, gold, graph_ready) provisioned via Terraform.

## When Making Changes (Examples)
- **Add a new source:** Update [configs/data-sources.yml](configs/data-sources.yml), adjust `csv-ingestion.py`, ensure validation rules in `data-validation.py`, and reflect any new graph mappings in `graph-transformation.py`.
- **Modify cluster sizing:** Edit per-env entries in [configs/cluster-configurations.yml](configs/cluster-configurations.yml); if changing Spark version/node type, update cluster resource in Terraform.
- **Extend the pipeline:** Add a new notebook and insert a dependent `task` in the Terraform job resource, preserving the DAG and base parameters.
- **Update Neo4j/Aura credentials:** Update GitHub repository secrets, then re-run the `06-data-pipeline.yml` workflow to sync to Databricks.

## Gotchas
- Ensure GitHub secrets are configured; missing credentials will fail Terraform apply.
- Tests assume keys in YAML configs; breaking schema in `configs/*.yml` will fail tests.
- Use single-environment naming across Terraform, configs, jobs, and GH Actions inputs.
- Unity Catalog must exist before running Terraform; Terraform will select first available or fail with clear error.

---
Questions or gaps? Tell me what feels unclear (e.g., missing commands, non-obvious approvals, or per-env overrides), and I'll refine this guide.
