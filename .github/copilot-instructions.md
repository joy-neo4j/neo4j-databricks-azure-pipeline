# Copilot Instructions: Neo4j + Databricks Azure Pipeline

## Scope & Big Picture
- **Purpose:** Production-ready ETL/analytics pipeline that ingests CSVs, validates/transforms into Bronze/Silver/Gold layers, converts to graph structures, and loads into Neo4j Aura.
- **Layers & Flow:** [databricks/notebooks](databricks/notebooks) run in order: `csv-ingestion.py` → `data-validation.py` → `graph-transformation.py` → `neo4j-loading.py`. This sequence is mirrored by jobs in [databricks/jobs/etl-pipeline-job.json](databricks/jobs/etl-pipeline-job.json#L1).
- **Orchestration:** GitHub Actions workflows in [.github/workflows](.github/workflows) drive end-to-end deploys (01→07). IaC resides in [terraform](terraform), runtime configs in [configs](configs), and ops docs in [docs](docs).

## Developer Workflows
- **Validate prerequisites:** `python scripts/validate-prerequisites.py` checks CLI tools, Azure login, structure; see [scripts/validate-prerequisites.py](scripts/validate-prerequisites.py#L1).
- **Local Databricks setup:**
  - Create/Update cluster: `ENVIRONMENT=dev ./scripts/setup-databricks-cluster.sh` ([scripts/setup-databricks-cluster.sh](scripts/setup-databricks-cluster.sh#L1))
  - Create ETL jobs: `ENVIRONMENT=dev ./scripts/create-databricks-jobs.sh` ([scripts/create-databricks-jobs.sh](scripts/create-databricks-jobs.sh#L1))
  - Run ETL: `ENVIRONMENT=prod ./scripts/run-etl-pipeline.sh` ([scripts/run-etl-pipeline.sh](scripts/run-etl-pipeline.sh#L1))
- **CI/CD deploys:** Trigger sequential workflows with `gh workflow run` per [README](README.md#L60). Key files: `02-azure-infrastructure.yml`, `03-neo4j-aura-setup.yml`, `04-databricks-configuration.yml`, `05-unity-catalog-setup.yml`, `06-data-pipeline.yml` in [.github/workflows](.github/workflows).
- **Tests:** `pytest tests/unit/` and `pytest tests/integration/`. Config shape expectations in [tests/test_pipeline.py](tests/test_pipeline.py#L1).

## Configuration Conventions
- **Terraform:** Environment vars via `terraform/environments/*.tfvars.example`. Required vars defined in [terraform/variables.tf](terraform/variables.tf#L1); keep `environment` one of `dev|staging|prod` and align resource naming/tagging per [docs/CONFIGURATION.md](docs/CONFIGURATION.md#L1).
- **Runtime configs:**
  - Data sources in [configs/data-sources.yml](configs/data-sources.yml) with `schema`, `validation` blocks.
  - Clusters per env in [configs/cluster-configurations.yml](configs/cluster-configurations.yml) (node types, workers, autotermination).
  - Monitoring alerts in [configs/monitoring-config.yml](configs/monitoring-config.yml).
- **Databricks job params:** Each notebook task passes `base_parameters: { environment }`; see [etl job](databricks/jobs/etl-pipeline-job.json#L9-L38). Preserve task ordering and dependencies.

## Secrets & Auth
- **Required secrets:** `AZURE_CREDENTIALS`, `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `DATABRICKS_TOKEN`, `AURA_CLIENT_ID`, `AURA_CLIENT_SECRET` (see [docs/SECRETS_MANAGEMENT.md](docs/SECRETS_MANAGEMENT.md#L1)).
- **Fallback pattern:** Prefer environment-scoped (e.g., `PROD_AZURE_CREDENTIALS`) then repository secrets; workflows use this format consistently.
- **Databricks CLI envs:** Set `DATABRICKS_HOST` and `DATABRICKS_TOKEN` before running scripts; Neo4j load script also needs `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` ([scripts/run-etl-pipeline.sh](scripts/run-etl-pipeline.sh#L1-L40)).
- **Secrets manager:** Interactive setup/validation via [scripts/secrets-manager.py](scripts/secrets-manager.py#L1).

## Patterns To Follow
- **Notebook order & idempotence:** Maintain the 4-stage notebook chain; don’t bypass validation before graph transforms. Use `batch_size` tuning only in `neo4j-loading` (see [etl job](databricks/jobs/etl-pipeline-job.json#L74-L103)).
- **Delta layers:**
  - Bronze: raw append-only tables.
  - Silver: cleaned/validated tables.
  - Gold: graph-ready nodes/relationships (naming like `neo4j_pipeline_{env}.gold.nodes`).
- **Terraform changes:** Keep variable validations intact and update env `*.tfvars.example` when adding new inputs; do not hardcode per-env values in `main.tf`.
- **Resource naming & tags:** Use conventions in [docs/CONFIGURATION.md](docs/CONFIGURATION.md#L100) for RG/Storage/KeyVault/Databricks; keep `ManagedBy=terraform`, `Environment`, `Project` tags.

## Integration Points
- **Databricks ↔ Neo4j:** Neo4j Spark connector installed via init scripts/libraries in cluster setup ([scripts/setup-databricks-cluster.sh](scripts/setup-databricks-cluster.sh#L24-L52)). Job `spark_conf` can reference Databricks secrets for Neo4j creds ([scripts/create-databricks-jobs.sh](scripts/create-databricks-jobs.sh#L74-L96)).
- **GitHub Actions:** Workflows sequence 01→07; use approvals for `staging/prod` per [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#L120).
- **Monitoring:** Alerts & logs configured via `configs/monitoring-config.yml`; operational queries/examples in [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md#L1).

## When Making Changes (Examples)
- **Add a new source:** Update [configs/data-sources.yml](configs/data-sources.yml), adjust `csv-ingestion.py`, ensure validation rules in `data-validation.py`, and reflect any new graph mappings in `graph-transformation.py`.
- **Modify cluster sizing:** Edit per-env entries in [configs/cluster-configurations.yml](configs/cluster-configurations.yml); if changing Spark version/node type, update job `new_cluster` blocks in [etl-pipeline-job.json](databricks/jobs/etl-pipeline-job.json) and `setup-databricks-cluster.sh`.
- **Extend the pipeline:** Add a new notebook and insert a dependent `task` in [etl-pipeline-job.json](databricks/jobs/etl-pipeline-job.json) preserving the DAG and base parameters.

## Gotchas
- Ensure CLI envs are set before running scripts; missing `DATABRICKS_HOST/TOKEN` or Neo4j envs will hard-fail the shell scripts.
- Tests assume keys in YAML configs; breaking schema in `configs/*.yml` will fail [tests/test_pipeline.py](tests/test_pipeline.py#L6-L36).
- Keep workflow names and environment labels (`dev|staging|prod`) consistent across Terraform, configs, jobs, and GH Actions inputs.

---
Questions or gaps? Tell me what feels unclear (e.g., missing commands, non-obvious approvals, or per-env overrides), and I’ll refine this guide.
