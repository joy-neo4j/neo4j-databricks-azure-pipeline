#!/usr/bin/env python3
"""
GitHub Secrets Manager for Neo4j-Databricks Pipeline
Manages repository and environment-specific secrets with validation and fallback mechanisms.
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional
import subprocess
import re
from datetime import datetime

class SecretsManager:
    """Manages GitHub secrets for the pipeline."""
    
    REQUIRED_SECRETS = {
        'AZURE_CREDENTIALS': {
            'description': 'Azure service principal credentials (JSON)',
            'validation': lambda v: SecretsManager._validate_json(v) and all(
                k in json.loads(v) for k in ['clientId', 'clientSecret', 'subscriptionId', 'tenantId']
            ),
            'sensitive': True
        },
        'AZURE_SUBSCRIPTION_ID': {
            'description': 'Azure subscription ID (UUID)',
            'validation': lambda v: SecretsManager._validate_uuid(v),
            'sensitive': False
        },
        'AZURE_TENANT_ID': {
            'description': 'Azure tenant ID (UUID)',
            'validation': lambda v: SecretsManager._validate_uuid(v),
            'sensitive': False
        },
        'DATABRICKS_TOKEN': {
            'description': 'Databricks personal access token',
            'validation': lambda v: v.startswith('dapi') and len(v) > 30,
            'sensitive': True
        },
        'AURA_CLIENT_ID': {
            'description': 'Neo4j Aura API client ID',
            'validation': lambda v: SecretsManager._validate_uuid(v),
            'sensitive': False
        },
        'AURA_CLIENT_SECRET': {
            'description': 'Neo4j Aura API client secret',
            'validation': lambda v: len(v) > 20,
            'sensitive': True
        }
    }
    
    OPTIONAL_SECRETS = {
        'SLACK_WEBHOOK_URL': {
            'description': 'Slack webhook URL for notifications',
            'validation': lambda v: v.startswith('https://hooks.slack.com/'),
            'sensitive': True
        },
        'NOTIFICATION_EMAIL': {
            'description': 'Email for deployment notifications',
            'validation': lambda v: '@' in v and '.' in v,
            'sensitive': False
        }
    }
    
    ENVIRONMENTS = ['dev', 'staging', 'prod']
    
    def __init__(self, repo_owner: str, repo_name: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.repo_full = f"{repo_owner}/{repo_name}"
    
    @staticmethod
    def _validate_json(value: str) -> bool:
        """Validate if string is valid JSON."""
        try:
            json.loads(value)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    @staticmethod
    def _validate_uuid(value: str) -> bool:
        """Validate if string is a valid UUID."""
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(value))
    
    def validate_secret(self, name: str, value: str) -> tuple[bool, str]:
        """Validate a secret value."""
        secrets_config = {**self.REQUIRED_SECRETS, **self.OPTIONAL_SECRETS}
        
        if name not in secrets_config:
            return False, f"Unknown secret: {name}"
        
        config = secrets_config[name]
        
        if not value or len(value.strip()) == 0:
            return False, f"Secret {name} is empty"
        
        if not config['validation'](value):
            return False, f"Secret {name} failed validation: {config['description']}"
        
        return True, "Valid"
    
    def set_repository_secret(self, name: str, value: str) -> bool:
        """Set a repository-level secret using gh CLI."""
        try:
            # Validate secret first
            is_valid, message = self.validate_secret(name, value)
            if not is_valid:
                print(f"❌ Validation failed: {message}")
                return False
            
            # Set secret using gh CLI
            result = subprocess.run(
                ['gh', 'secret', 'set', name, '--repo', self.repo_full],
                input=value.encode(),
                capture_output=True
            )
            
            if result.returncode == 0:
                print(f"✅ Set repository secret: {name}")
                return True
            else:
                print(f"❌ Failed to set secret {name}: {result.stderr.decode()}")
                return False
        
        except Exception as e:
            print(f"❌ Error setting secret {name}: {e}")
            return False
    
    def set_environment_secret(self, environment: str, name: str, value: str) -> bool:
        """Set an environment-specific secret using gh CLI."""
        try:
            if environment not in self.ENVIRONMENTS:
                print(f"❌ Invalid environment: {environment}")
                return False
            
            # Validate secret first
            is_valid, message = self.validate_secret(name, value)
            if not is_valid:
                print(f"❌ Validation failed: {message}")
                return False
            
            # Set secret using gh CLI
            result = subprocess.run(
                ['gh', 'secret', 'set', name, '--env', environment, '--repo', self.repo_full],
                input=value.encode(),
                capture_output=True
            )
            
            if result.returncode == 0:
                print(f"✅ Set {environment} environment secret: {name}")
                return True
            else:
                print(f"❌ Failed to set secret {name}: {result.stderr.decode()}")
                return False
        
        except Exception as e:
            print(f"❌ Error setting secret {name}: {e}")
            return False
    
    def list_secrets(self) -> Dict[str, List[str]]:
        """List all configured secrets."""
        try:
            result = subprocess.run(
                ['gh', 'secret', 'list', '--repo', self.repo_full],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to list secrets: {result.stderr}")
                return {}
            
            secrets = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split()
                    if parts:
                        secrets[parts[0]] = parts[1:] if len(parts) > 1 else []
            
            return secrets
        
        except Exception as e:
            print(f"❌ Error listing secrets: {e}")
            return {}
    
    def validate_all_secrets(self) -> bool:
        """Validate that all required secrets are configured."""
        secrets = self.list_secrets()
        missing_secrets = []
        
        print("\n📋 Checking required secrets...")
        for secret_name in self.REQUIRED_SECRETS:
            if secret_name not in secrets:
                # Check for environment-specific versions
                has_env_specific = any(
                    f"{env.upper()}_{secret_name}" in secrets 
                    for env in self.ENVIRONMENTS
                )
                
                if not has_env_specific:
                    missing_secrets.append(secret_name)
                    print(f"❌ Missing: {secret_name}")
                else:
                    print(f"✅ {secret_name} (via environment-specific secrets)")
            else:
                print(f"✅ {secret_name}")
        
        if missing_secrets:
            print(f"\n❌ Missing {len(missing_secrets)} required secret(s)")
            return False
        
        print("\n✅ All required secrets are configured")
        return True
    
    def setup_interactive(self):
        """Interactive setup for secrets."""
        print("🔐 Neo4j-Databricks Pipeline Secrets Setup")
        print("=" * 60)
        
        for secret_name, config in self.REQUIRED_SECRETS.items():
            print(f"\n📝 {secret_name}")
            print(f"   {config['description']}")
            
            if config['sensitive']:
                import getpass
                value = getpass.getpass("   Enter value (hidden): ")
            else:
                value = input("   Enter value: ")
            
            is_valid, message = self.validate_secret(secret_name, value)
            if not is_valid:
                print(f"   ❌ {message}")
                continue
            
            self.set_repository_secret(secret_name, value)
        
        print("\n" + "=" * 60)
        print("✅ Required secrets setup complete!")
        
        # Optional secrets
        print("\n📋 Optional Secrets")
        setup_optional = input("Setup optional secrets? (y/n): ").lower() == 'y'
        
        if setup_optional:
            for secret_name, config in self.OPTIONAL_SECRETS.items():
                print(f"\n📝 {secret_name}")
                print(f"   {config['description']}")
                
                if config['sensitive']:
                    import getpass
                    value = getpass.getpass("   Enter value (hidden, press Enter to skip): ")
                else:
                    value = input("   Enter value (press Enter to skip): ")
                
                if value:
                    is_valid, message = self.validate_secret(secret_name, value)
                    if not is_valid:
                        print(f"   ❌ {message}")
                        continue
                    
                    self.set_repository_secret(secret_name, value)

def main():
    parser = argparse.ArgumentParser(
        description='Manage GitHub secrets for Neo4j-Databricks Pipeline'
    )
    parser.add_argument(
        '--repo',
        required=True,
        help='Repository in format owner/name'
    )
    parser.add_argument(
        '--action',
        choices=['validate', 'setup', 'list'],
        default='validate',
        help='Action to perform'
    )
    parser.add_argument(
        '--environment',
        choices=['dev', 'staging', 'prod'],
        help='Environment for environment-specific secrets'
    )
    
    args = parser.parse_args()
    
    # Parse repository
    if '/' not in args.repo:
        print("❌ Repository must be in format owner/name")
        sys.exit(1)
    
    owner, name = args.repo.split('/', 1)
    manager = SecretsManager(owner, name)
    
    if args.action == 'validate':
        if not manager.validate_all_secrets():
            sys.exit(1)
    
    elif args.action == 'setup':
        manager.setup_interactive()
    
    elif args.action == 'list':
        secrets = manager.list_secrets()
        print("\n📋 Configured Secrets:")
        for secret_name in sorted(secrets.keys()):
            print(f"  ✅ {secret_name}")

if __name__ == '__main__':
    main()
