"""
Test Terraform stability improvements in 02-provision workflow
"""
import yaml
import pytest


class TestTerraformStability:
    """Test Terraform stability improvements for state lock handling"""
    
    def test_lease_break_step_exists(self):
        """Test that the lease break step exists in the workflow"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        step_names = [step.get('name', '') for step in steps]
        
        assert 'Break stale Terraform state lease (best effort)' in step_names, \
            "Lease break step not found in workflow"
    
    def test_lease_break_step_position(self):
        """Test that lease break step is between backend bootstrap and Terraform Init"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        step_names = [step.get('name', '') for step in steps]
        
        backend_bootstrap_idx = step_names.index('Ensure Terraform remote backend resources exist')
        lease_break_idx = step_names.index('Break stale Terraform state lease (best effort)')
        terraform_init_idx = step_names.index('Terraform Init')
        
        assert backend_bootstrap_idx < lease_break_idx < terraform_init_idx, \
            "Lease break step must be between backend bootstrap and Terraform Init"
    
    def test_lease_break_step_content(self):
        """Test that lease break step has correct content"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        
        # Find the lease break step
        lease_break_step = None
        for step in steps:
            if step.get('name') == 'Break stale Terraform state lease (best effort)':
                lease_break_step = step
                break
        
        assert lease_break_step is not None, "Lease break step not found"
        assert 'run' in lease_break_step, "Lease break step must have 'run' field"
        
        script = lease_break_step['run']
        
        # Check for required content
        assert 'set -euo pipefail' in script, "Error handling not set up properly"
        assert 'BACKEND_STORAGE_ACCOUNT' in script, "BACKEND_STORAGE_ACCOUNT not referenced"
        assert 'az storage blob lease break' in script, "Lease break command not found"
        assert 'tfstate' in script, "Container name not found"
        assert 'neo4j-databricks-dev.tfstate' in script, "State file name not found"
        assert '|| true' in script, "Best-effort failure handling not found"
    
    def test_terraform_plan_has_lock_timeout_10m(self):
        """Test that Terraform Plan step has 10m lock timeout"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        
        # Find the Terraform Plan step
        plan_step = None
        for step in steps:
            if step.get('name') == 'Terraform Plan':
                plan_step = step
                break
        
        assert plan_step is not None, "Terraform Plan step not found"
        assert 'run' in plan_step, "Terraform Plan step must have 'run' field"
        
        script = plan_step['run']
        assert '-lock-timeout=10m' in script, "Terraform Plan should have -lock-timeout=10m"
    
    def test_terraform_apply_has_lock_timeout_10m(self):
        """Test that Terraform Apply step has 10m lock timeout"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        
        # Find the Terraform Apply step
        apply_step = None
        for step in steps:
            if step.get('name') == 'Terraform Apply':
                apply_step = step
                break
        
        assert apply_step is not None, "Terraform Apply step not found"
        assert 'run' in apply_step, "Terraform Apply step must have 'run' field"
        
        script = apply_step['run']
        assert '-lock-timeout=10m' in script, "Terraform Apply should have -lock-timeout=10m"
    
    def test_terraform_plan_has_environment_var(self):
        """Test that Terraform Plan step has TF_VAR_environment set"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        
        # Find the Terraform Plan step
        plan_step = None
        for step in steps:
            if step.get('name') == 'Terraform Plan':
                plan_step = step
                break
        
        assert plan_step is not None, "Terraform Plan step not found"
        assert 'env' in plan_step, "Terraform Plan step must have 'env' field"
        
        env_vars = plan_step['env']
        assert 'TF_VAR_environment' in env_vars, "TF_VAR_environment not found in Plan env"
        assert env_vars['TF_VAR_environment'] == 'dev', "TF_VAR_environment should be 'dev'"
    
    def test_terraform_apply_has_environment_var(self):
        """Test that Terraform Apply step has TF_VAR_environment set"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        
        # Find the Terraform Apply step
        apply_step = None
        for step in steps:
            if step.get('name') == 'Terraform Apply':
                apply_step = step
                break
        
        assert apply_step is not None, "Terraform Apply step not found"
        assert 'env' in apply_step, "Terraform Apply step must have 'env' field"
        
        env_vars = apply_step['env']
        assert 'TF_VAR_environment' in env_vars, "TF_VAR_environment not found in Apply env"
        assert env_vars['TF_VAR_environment'] == 'dev', "TF_VAR_environment should be 'dev'"
    
    def test_terraform_plan_has_input_false(self):
        """Test that Terraform Plan has -input=false flag"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        
        # Find the Terraform Plan step
        plan_step = None
        for step in steps:
            if step.get('name') == 'Terraform Plan':
                plan_step = step
                break
        
        assert plan_step is not None, "Terraform Plan step not found"
        script = plan_step['run']
        assert '-input=false' in script, "Terraform Plan should have -input=false"
    
    def test_terraform_apply_has_input_false(self):
        """Test that Terraform Apply has -input=false flag"""
        with open(".github/workflows/02-provision.yml", 'r') as f:
            workflow = yaml.safe_load(f)
        
        provision_job = workflow['jobs']['provision']
        steps = provision_job['steps']
        
        # Find the Terraform Apply step
        apply_step = None
        for step in steps:
            if step.get('name') == 'Terraform Apply':
                apply_step = step
                break
        
        assert apply_step is not None, "Terraform Apply step not found"
        script = apply_step['run']
        assert '-input=false' in script, "Terraform Apply should have -input=false"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
