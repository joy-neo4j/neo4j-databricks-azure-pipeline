#!/usr/bin/env python3
"""
Validate Prerequisites Script
Checks that all prerequisites are met before deployment
"""

import subprocess
import sys
import os
import json
from typing import Tuple, List

def check_command(command: str, min_version: str = None) -> Tuple[bool, str]:
    """Check if a command exists and optionally verify minimum version."""
    try:
        result = subprocess.run(
            [command, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version_output = result.stdout or result.stderr
            return True, version_output.split('\n')[0]
        return False, "Command not found"
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "Command not found"

def check_azure_login() -> Tuple[bool, str]:
    """Check if Azure CLI is logged in."""
    try:
        result = subprocess.run(
            ['az', 'account', 'show'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            account_info = json.loads(result.stdout)
            return True, f"Logged in as: {account_info.get('user', {}).get('name', 'unknown')}"
        return False, "Not logged in"
    
    except Exception as e:
        return False, str(e)

def check_environment_variables(required_vars: List[str]) -> Tuple[bool, List[str]]:
    """Check if required environment variables are set."""
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    return len(missing) == 0, missing

def main():
    print("🔍 Validating Prerequisites for Neo4j-Databricks Pipeline")
    print("=" * 70)
    
    all_checks_passed = True
    
    # Check required commands
    commands = {
        'az': '2.40.0',
        'terraform': '1.5.0',
        'python3': '3.8',
        'gh': None
    }
    
    print("\n📦 Checking Required Commands:")
    for cmd, min_version in commands.items():
        exists, info = check_command(cmd)
        if exists:
            print(f"  ✅ {cmd}: {info}")
        else:
            print(f"  ❌ {cmd}: Not found")
            all_checks_passed = False
    
    # Check Azure login
    print("\n🔐 Checking Azure Authentication:")
    logged_in, info = check_azure_login()
    if logged_in:
        print(f"  ✅ Azure CLI: {info}")
    else:
        print(f"  ❌ Azure CLI: {info}")
        print("     Run: az login")
        all_checks_passed = False
    
    # Check optional environment variables
    print("\n🌍 Checking Environment Variables:")
    optional_vars = ['DATABRICKS_HOST', 'DATABRICKS_TOKEN', 'NEO4J_URI']
    for var in optional_vars:
        if os.getenv(var):
            print(f"  ✅ {var}: Set")
        else:
            print(f"  ℹ️  {var}: Not set (will use GitHub secrets)")
    
    # Check file structure
    print("\n📁 Checking Project Structure:")
    required_paths = [
        'terraform/main.tf',
        'terraform/variables.tf',
        '.github/workflows/deploy-full-pipeline.yml',
        'databricks/notebooks',
        'scripts/secrets-manager.py'
    ]
    
    for path in required_paths:
        full_path = os.path.join(os.getcwd(), path)
        if os.path.exists(full_path):
            print(f"  ✅ {path}")
        else:
            print(f"  ❌ {path}: Not found")
            all_checks_passed = False
    
    print("\n" + "=" * 70)
    
    if all_checks_passed:
        print("✅ All prerequisites validated successfully!")
        print("\nNext steps:")
        print("  1. Configure GitHub secrets: python scripts/secrets-manager.py --repo owner/name --action setup")
        print("  2. Deploy infrastructure: gh workflow run deploy-full-pipeline.yml -f environment=dev")
        return 0
    else:
        print("❌ Some prerequisites are not met. Please resolve the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
