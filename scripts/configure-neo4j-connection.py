#!/usr/bin/env python3
"""
Configure Neo4j Connection Script
Tests and configures Neo4j Aura connection for Databricks
"""

import argparse
import sys
from neo4j import GraphDatabase
import os

def test_connection(uri: str, username: str, password: str) -> bool:
    """Test Neo4j connection."""
    try:
        print(f"🔌 Testing connection to {uri}...")
        
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            value = result.single()["test"]
            
            if value == 1:
                print("✅ Connection successful!")
                
                # Get database info
                result = session.run("CALL dbms.components() YIELD name, versions, edition")
                for record in result:
                    print(f"   Neo4j {record['name']}: {record['versions'][0]} ({record['edition']})")
                
                driver.close()
                return True
        
        driver.close()
        return False
    
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def setup_constraints(uri: str, username: str, password: str) -> bool:
    """Set up Neo4j constraints and indexes."""
    try:
        print("🔧 Setting up database constraints...")
        
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        constraints = [
            "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT order_id IF NOT EXISTS FOR (o:Order) REQUIRE o.id IS UNIQUE"
        ]
        
        indexes = [
            "CREATE INDEX customer_name IF NOT EXISTS FOR (c:Customer) ON (c.name)",
            "CREATE INDEX product_name IF NOT EXISTS FOR (p:Product) ON (p.name)",
            "CREATE INDEX order_date IF NOT EXISTS FOR (o:Order) ON (o.order_date)"
        ]
        
        with driver.session() as session:
            for constraint in constraints:
                session.run(constraint)
                print(f"   ✅ {constraint.split()[2]}")
            
            for index in indexes:
                session.run(index)
                print(f"   ✅ {index.split()[2]}")
        
        driver.close()
        print("✅ Database setup complete!")
        return True
    
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Configure Neo4j connection')
    parser.add_argument('--uri', help='Neo4j URI', default=os.getenv('NEO4J_URI'))
    parser.add_argument('--username', help='Neo4j username', default=os.getenv('NEO4J_USERNAME', 'neo4j'))
    parser.add_argument('--password', help='Neo4j password', default=os.getenv('NEO4J_PASSWORD'))
    parser.add_argument('--test', action='store_true', help='Test connection only')
    parser.add_argument('--setup', action='store_true', help='Setup constraints and indexes')
    
    args = parser.parse_args()
    
    if not all([args.uri, args.username, args.password]):
        print("❌ Error: URI, username, and password are required")
        print("   Set via --uri, --username, --password or environment variables")
        sys.exit(1)
    
    # Test connection
    if not test_connection(args.uri, args.username, args.password):
        sys.exit(1)
    
    # Setup if requested
    if args.setup or not args.test:
        if not setup_constraints(args.uri, args.username, args.password):
            sys.exit(1)

if __name__ == '__main__':
    main()
