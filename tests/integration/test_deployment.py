"""
Integration tests for deployment
"""
import pytest
import subprocess
import os


class TestDeployment:
    """Test deployment workflows and infrastructure"""
    
    def test_terraform_validate(self):
        """Test Terraform configuration is valid"""
        result = subprocess.run(
            ["terraform", "validate"],
            cwd="terraform",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Terraform validation failed: {result.stderr}"
    
    def test_required_files_exist(self):
        """Test that all required files exist"""
        required_files = [
            "README.md",
            "terraform/main.tf",
            "terraform/variables.tf",
            "terraform/outputs.tf",
            ".github/workflows/deploy-full-pipeline.yml",
            "scripts/secrets-manager.py",
            "databricks/notebooks/csv-ingestion.py",
            "configs/data-sources.yml",
        ]
        
        for file_path in required_files:
            assert os.path.exists(file_path), f"Required file not found: {file_path}"
    
    def test_workflow_syntax(self):
        """Test GitHub workflow YAML syntax"""
        import yaml
        
        workflows = [
            ".github/workflows/deploy-full-pipeline.yml",
            ".github/workflows/deploy-infrastructure.yml",
            ".github/workflows/deploy-data-pipeline.yml"
        ]
        
        for workflow_path in workflows:
            with open(workflow_path, 'r') as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {workflow_path}: {e}")
    
    def test_sample_data_format(self):
        """Test sample CSV data is valid"""
        import csv
        
        csv_files = [
            "sample-data/customers.csv",
            "sample-data/products.csv",
            "sample-data/orders.csv"
        ]
        
        for csv_file in csv_files:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) > 0, f"No data in {csv_file}"
                assert len(reader.fieldnames) > 0, f"No headers in {csv_file}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
