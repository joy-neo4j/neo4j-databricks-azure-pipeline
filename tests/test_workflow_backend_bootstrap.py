"""
Test workflow backend bootstrap step
"""
import yaml
import pytest


class TestWorkflowBackendBootstrap:
    """Test 02-provision workflow backend bootstrap step"""
    
    def test_provision_workflow_has_backend_bootstrap_step(self):
        """Test that the provision workflow has the backend bootstrap step"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        # Get the provision job
        assert 'jobs' in workflow
        assert 'provision' in workflow['jobs']
        
        provision_job = workflow['jobs']['provision']
        assert 'steps' in provision_job
        
        # Find the backend bootstrap step
        steps = provision_job['steps']
        step_names = [step.get('name', '') for step in steps]
        
        assert 'Ensure Terraform remote backend resources exist' in step_names, \
            "Backend bootstrap step not found in workflow"
    
    def test_backend_bootstrap_step_position(self):
        """Test that backend bootstrap step is between Azure Login and Terraform Init"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        step_names = [step.get('name', '') for step in steps]
        
        azure_login_idx = step_names.index('Azure Login')
        backend_bootstrap_idx = step_names.index('Ensure Terraform remote backend resources exist')
        terraform_init_idx = step_names.index('Terraform Init')
        
        assert azure_login_idx < backend_bootstrap_idx < terraform_init_idx, \
            "Backend bootstrap step must be between Azure Login and Terraform Init"
    
    def test_backend_bootstrap_step_script_content(self):
        """Test that backend bootstrap step has correct script content"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        
        # Find the backend bootstrap step
        backend_step = None
        for step in steps:
            if step.get('name') == 'Ensure Terraform remote backend resources exist':
                backend_step = step
                break
        
        assert backend_step is not None, "Backend bootstrap step not found"
        assert 'run' in backend_step, "Backend bootstrap step must have 'run' field"
        
        script = backend_step['run']
        
        # Check for required variables
        assert 'rg-terraform-state' in script, "Resource group name not found in script"
        assert 'BASE="tfstate"' in script, "Storage account base name not found in script"
        assert 'SUB_NAME=' in script, "Subscription name computation not found in script"
        assert 'az account show' in script, "Azure subscription query not found in script"
        assert 'BACKEND_STORAGE_ACCOUNT=' in script, "BACKEND_STORAGE_ACCOUNT export not found in script"
        assert 'tfstate' in script, "Container name not found in script"
        assert 'uksouth' in script, "Location not found in script"
        
        # Check for required Azure CLI commands
        assert 'az group show' in script, "Resource group check not found"
        assert 'az group create' in script, "Resource group creation not found"
        assert 'az storage account show' in script, "Storage account check not found"
        assert 'az storage account create' in script, "Storage account creation not found"
        assert 'az storage container show' in script, "Container check not found"
        assert 'az storage container create' in script, "Container creation not found"
        
        # Check for error handling
        assert 'set -euo pipefail' in script, "Error handling not set up properly"
    
    def test_configure_backend_step_exists(self):
        """Test that the Configure Terraform Backend step exists"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        step_names = [step.get('name', '') for step in steps]
        
        assert 'Configure Terraform Backend' in step_names, \
            "Configure Terraform Backend step not found in workflow"
    
    def test_configure_backend_uses_env_variable(self):
        """Test that Configure Terraform Backend step uses BACKEND_STORAGE_ACCOUNT env variable"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        
        # Find the Configure Terraform Backend step
        backend_config_step = None
        for step in steps:
            if step.get('name') == 'Configure Terraform Backend':
                backend_config_step = step
                break
        
        assert backend_config_step is not None, "Configure Terraform Backend step not found"
        assert 'run' in backend_config_step, "Configure Terraform Backend step must have 'run' field"
        
        script = backend_config_step['run']
        
        # Check that it creates backend.tf with dynamic storage account name
        assert 'backend.tf' in script, "backend.tf creation not found"
        assert 'backend "azurerm"' in script, "azurerm backend not found"
        assert '${BACKEND_STORAGE_ACCOUNT}' in script, "BACKEND_STORAGE_ACCOUNT variable not used"
        assert 'rg-terraform-state' in script, "Resource group not found in backend config"
    
    def test_upload_sample_data_step_exists(self):
        """Test that the Upload Storage Sample Data step exists"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        step_names = [step.get('name', '') for step in steps]
        
        assert 'Upload Storage Sample Data' in step_names, \
            "Upload Storage Sample Data step not found in workflow"
    
    def test_upload_sample_data_uses_env_variable(self):
        """Test that Upload Storage Sample Data step uses BACKEND_STORAGE_ACCOUNT env variable"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        
        # Find the Upload Storage Sample Data step
        upload_step = None
        for step in steps:
            if step.get('name') == 'Upload Storage Sample Data':
                upload_step = step
                break
        
        assert upload_step is not None, "Upload Storage Sample Data step not found"
        assert 'run' in upload_step, "Upload Storage Sample Data step must have 'run' field"
        
        script = upload_step['run']
        
        # Check that it uses env.BACKEND_STORAGE_ACCOUNT
        assert 'az storage blob upload-batch' in script, "Blob upload command not found"
        assert '${{ env.BACKEND_STORAGE_ACCOUNT }}' in script, "BACKEND_STORAGE_ACCOUNT env variable not used"
        assert 'sample-data' in script, "sample-data source not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
