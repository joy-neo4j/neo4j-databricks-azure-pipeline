# Databricks notebook source
# MAGIC %md
# MAGIC # Neo4j Constraints and Indexes Setup
# MAGIC 
# MAGIC This notebook creates constraints and indexes in Neo4j for the e-commerce data model.
# MAGIC - Customer nodes
# MAGIC - Product nodes
# MAGIC - Order nodes

# COMMAND ----------

# Install neo4j driver
# %pip install neo4j

# COMMAND ----------

from neo4j import GraphDatabase
import sys

# COMMAND ----------

# Read secrets from Databricks secret scope
neo4j_uri = dbutils.secrets.get(scope="pipeline-secrets", key="neo4j-uri")
neo4j_username = dbutils.secrets.get(scope="pipeline-secrets", key="neo4j-username")
neo4j_password = dbutils.secrets.get(scope="pipeline-secrets", key="neo4j-password")

if not neo4j_uri or not neo4j_username or not neo4j_password:
    raise ValueError("Neo4j connection secrets not found. Ensure 'pipeline-secrets' scope contains required keys.")

print(f"✓ Neo4j URI: {neo4j_uri[:20]}...")

# COMMAND ----------

# Connect to Neo4j
driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

def verify_connection():
    """Verify Neo4j connection"""
    try:
        driver.verify_connectivity()
        print("✓ Neo4j connection verified")
        return True
    except Exception as e:
        print(f"✗ Neo4j connection failed: {e}")
        return False

if not verify_connection():
    raise ConnectionError("Cannot connect to Neo4j")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Constraints

# COMMAND ----------

def create_constraint(tx, constraint_query):
    """Create a constraint in Neo4j"""
    try:
        tx.run(constraint_query)
        return True
    except Exception as e:
        # Constraint might already exist
        if "already exists" in str(e) or "An equivalent constraint already exists" in str(e):
            return False
        else:
            raise e

constraints = [
    # Customer constraints
    "CREATE CONSTRAINT customer_id_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE",
    "CREATE CONSTRAINT customer_email_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.email IS UNIQUE",
    
    # Product constraints
    "CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
    "CREATE CONSTRAINT product_sku_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.sku IS UNIQUE",
    
    # Order constraints
    "CREATE CONSTRAINT order_id_unique IF NOT EXISTS FOR (o:Order) REQUIRE o.order_id IS UNIQUE",
    
    # Category constraints
    "CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.category_id IS UNIQUE",
]

with driver.session() as session:
    for constraint in constraints:
        try:
            result = session.execute_write(create_constraint, constraint)
            constraint_name = constraint.split("CONSTRAINT")[1].split("IF NOT EXISTS")[0].strip()
            if result:
                print(f"✓ Created constraint: {constraint_name}")
            else:
                print(f"→ Constraint already exists: {constraint_name}")
        except Exception as e:
            print(f"✗ Error creating constraint: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Indexes

# COMMAND ----------

def create_index(tx, index_query):
    """Create an index in Neo4j"""
    try:
        tx.run(index_query)
        return True
    except Exception as e:
        # Index might already exist
        if "already exists" in str(e) or "An equivalent index already exists" in str(e):
            return False
        else:
            raise e

indexes = [
    # Customer indexes
    "CREATE INDEX customer_name_idx IF NOT EXISTS FOR (c:Customer) ON (c.name)",
    "CREATE INDEX customer_segment_idx IF NOT EXISTS FOR (c:Customer) ON (c.segment)",
    
    # Product indexes
    "CREATE INDEX product_name_idx IF NOT EXISTS FOR (p:Product) ON (p.name)",
    "CREATE INDEX product_category_idx IF NOT EXISTS FOR (p:Product) ON (p.category)",
    "CREATE INDEX product_price_idx IF NOT EXISTS FOR (p:Product) ON (p.price)",
    
    # Order indexes
    "CREATE INDEX order_date_idx IF NOT EXISTS FOR (o:Order) ON (o.order_date)",
    "CREATE INDEX order_status_idx IF NOT EXISTS FOR (o:Order) ON (o.status)",
]

with driver.session() as session:
    for index in indexes:
        try:
            result = session.execute_write(create_index, index)
            index_name = index.split("INDEX")[1].split("IF NOT EXISTS")[0].strip()
            if result:
                print(f"✓ Created index: {index_name}")
            else:
                print(f"→ Index already exists: {index_name}")
        except Exception as e:
            print(f"✗ Error creating index: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Constraints and Indexes

# COMMAND ----------

with driver.session() as session:
    # Show constraints
    result = session.run("SHOW CONSTRAINTS")
    constraints_count = sum(1 for _ in result)
    print(f"\n✓ Total constraints: {constraints_count}")
    
    # Show indexes
    result = session.run("SHOW INDEXES")
    indexes_count = sum(1 for _ in result)
    print(f"✓ Total indexes: {indexes_count}")

# COMMAND ----------

# Close the driver
driver.close()
print("\n✓ Neo4j constraints and indexes setup complete")
