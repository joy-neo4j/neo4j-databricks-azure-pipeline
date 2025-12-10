#!/usr/bin/env python3
"""
Setup Unity Catalog Script
Configures Unity Catalog for Databricks workspace
"""

import sys
import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import *

def setup_unity_catalog(workspace_url: str, token: str, environment: str):
    """Setup Unity Catalog for the workspace."""
    
    print(f"🔧 Setting up Unity Catalog for {environment}")
    
    try:
        w = WorkspaceClient(host=workspace_url, token=token)
        
        # Create catalog
        catalog_name = f"neo4j_pipeline_{environment}"
        print(f"Creating catalog: {catalog_name}")
        
        try:
            catalog = w.catalogs.create(
                name=catalog_name,
                comment=f"Neo4j Pipeline catalog for {environment}",
                properties={"environment": environment}
            )
            print(f"  ✅ Catalog created: {catalog.name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  ℹ️  Catalog already exists")
            else:
                raise
        
        # Create schemas
        schemas = ['bronze', 'silver', 'gold', 'neo4j']
        
        for schema_name in schemas:
            print(f"Creating schema: {schema_name}")
            try:
                schema = w.schemas.create(
                    catalog_name=catalog_name,
                    name=schema_name,
                    comment=f"{schema_name.capitalize()} layer for data processing"
                )
                print(f"  ✅ Schema created: {schema.name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  ℹ️  Schema already exists")
                else:
                    raise
        
        # Grant permissions
        print("Setting up permissions...")
        # Add permission logic here
        
        print("✅ Unity Catalog setup complete!")
        return True
    
    except Exception as e:
        print(f"❌ Error setting up Unity Catalog: {e}")
        return False

def main():
    workspace_url = os.getenv('DATABRICKS_HOST')
    token = os.getenv('DATABRICKS_TOKEN')
    environment = sys.argv[1] if len(sys.argv) > 1 else 'dev'
    
    if not workspace_url or not token:
        print("❌ Error: DATABRICKS_HOST and DATABRICKS_TOKEN environment variables must be set")
        sys.exit(1)
    
    if not setup_unity_catalog(workspace_url, token, environment):
        sys.exit(1)

if __name__ == '__main__':
    main()
