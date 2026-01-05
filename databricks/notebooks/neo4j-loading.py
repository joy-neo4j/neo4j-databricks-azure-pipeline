# Databricks notebook source
# MAGIC %md
# MAGIC # Neo4j Loading (Graph Ready → Neo4j)
# MAGIC 
# MAGIC Reads {catalog}.graph_ready.* and loads into Neo4j Aura.
# MAGIC 
# MAGIC Parameters:
# MAGIC - `catalog`: Unity Catalog name (optional)
# MAGIC - `batch_size`: Batch size for loading (default: 1000)

# COMMAND ----------

from pyspark.sql import functions as F
from neo4j import GraphDatabase
import json
import os

# Get parameters
dbutils.widgets.text("catalog", "", "Unity Catalog name")
dbutils.widgets.text("batch_size", "1000", "Batch Size")

catalog_param = dbutils.widgets.get("catalog")
batch_size = int(dbutils.widgets.get("batch_size"))

print(f"Batch Size: {batch_size}")

# Catalog resolution
def _get_catalog_names():
    try:
        df = spark.sql("SHOW CATALOGS")
        names = []
        for r in df.collect():
            for attr in ("catalog_name","catalog","name"):
                if hasattr(r, attr):
                    names.append(getattr(r, attr)); break
        return names
    except Exception:
        return []

catalog_names = _get_catalog_names()
preferred_catalog = "neo4j_pipeline"
CATALOG = catalog_param or (preferred_catalog if preferred_catalog in catalog_names else (catalog_names[0] if catalog_names else preferred_catalog))
spark.sql(f"USE CATALOG {CATALOG}")
print(f"Using catalog: {CATALOG}")

# COMMAND ----------
# Get Neo4j credentials from Databricks secrets

try:
    neo4j_uri = dbutils.secrets.get(scope="pipeline-secrets", key="neo4j-uri")
    neo4j_username = dbutils.secrets.get(scope="pipeline-secrets", key="neo4j-username")
    neo4j_password = dbutils.secrets.get(scope="pipeline-secrets", key="neo4j-password")
    
    print(f"✅ Neo4j credentials loaded from secrets")
    print(f"URI: {neo4j_uri}")
    print(f"Username: {neo4j_username}")
except Exception as e:
    print(f"❌ Error loading secrets: {str(e)}")
    print("Make sure Neo4j secrets are configured in Databricks")
    dbutils.notebook.exit("FAILED: Missing Neo4j credentials")

# COMMAND ----------
# Test Neo4j connection

def test_neo4j_connection(uri, username, password):
    """Test Neo4j connection."""
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            value = result.single()["test"]
            
            if value == 1:
                print("✅ Neo4j connection successful")
                
                # Get database info
                result = session.run("CALL dbms.components() YIELD name, versions, edition")
                for record in result:
                    print(f"   {record['name']}: {record['versions'][0]} ({record['edition']})")
                
                driver.close()
                return True
        
        driver.close()
        return False
    
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

if not test_neo4j_connection(neo4j_uri, neo4j_username, neo4j_password):
    dbutils.notebook.exit("FAILED: Cannot connect to Neo4j")

# COMMAND ----------
# Read graph_ready tables and normalize to expected schemas

cust_nodes = spark.table(f"{CATALOG}.graph_ready.customer_nodes").select(
    F.col("node_id"), F.col("properties"), F.lit("Customer").alias("node_label")
)
prod_nodes = spark.table(f"{CATALOG}.graph_ready.product_nodes").select(
    F.col("node_id"), F.col("properties"), F.lit("Product").alias("node_label")
)
nodes_df = cust_nodes.unionByName(prod_nodes)
print(f"Nodes to load: {nodes_df.count()}")

purchased = spark.table(f"{CATALOG}.graph_ready.purchased_relationships").select(
    F.col("from_id").alias("source_node_id"),
    F.lit("Customer").alias("source_node_label"),
    F.col("to_id").alias("target_node_id"),
    F.lit("Product").alias("target_node_label"),
    F.lit("PURCHASED").alias("relationship_type"),
    F.col("properties")
)
reviewed = spark.table(f"{CATALOG}.graph_ready.reviewed_relationships").select(
    F.col("from_id").alias("source_node_id"),
    F.lit("Customer").alias("source_node_label"),
    F.col("to_id").alias("target_node_id"),
    F.lit("Product").alias("target_node_label"),
    F.lit("REVIEWED").alias("relationship_type"),
    F.col("properties")
)
relationships_df = purchased.unionByName(reviewed)
print(f"Relationships to load: {relationships_df.count()}")

# COMMAND ----------
# Setup constraints in Neo4j

def setup_neo4j_constraints(uri, username, password):
    """Create constraints and indexes in Neo4j."""
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    constraints = [
        "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE"
    ]
    
    indexes = [
        "CREATE INDEX customer_name IF NOT EXISTS FOR (c:Customer) ON (c.name)",
        "CREATE INDEX product_name IF NOT EXISTS FOR (p:Product) ON (p.name)"
    ]
    
    try:
        with driver.session() as session:
            print("\n📋 Creating constraints...")
            for constraint in constraints:
                session.run(constraint)
                print(f"  ✅ {constraint.split()[2]}")
            
            print("\n📋 Creating indexes...")
            for index in indexes:
                session.run(index)
                print(f"  ✅ {index.split()[2]}")
        
        print("\n✅ Database schema setup complete")
        driver.close()
        return True
    
    except Exception as e:
        print(f"❌ Error setting up schema: {str(e)}")
        driver.close()
        return False

setup_neo4j_constraints(neo4j_uri, neo4j_username, neo4j_password)

# COMMAND ----------
# Load nodes to Neo4j

def load_nodes_to_neo4j(nodes_df, uri, username, password, batch_size):
    """Load nodes to Neo4j in batches."""
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    # Group by node label
    node_labels = nodes_df.select("node_label").distinct().collect()
    
    total_loaded = 0
    
    for row in node_labels:
        label = row['node_label']
        label_df = nodes_df.filter(F.col("node_label") == label)
        
        # Collect in batches
        total_count = label_df.count()
        print(f"\n📦 Loading {total_count} {label} nodes...")
        
        # Convert to list of dictionaries
        nodes_data = label_df.select("node_id", "properties").collect()
        
        # Process in batches
        for i in range(0, len(nodes_data), batch_size):
            batch = nodes_data[i:i+batch_size]
            
            try:
                with driver.session() as session:
                    # Create merge query
                    query = f"""
                    UNWIND $nodes AS node
                    MERGE (n:{label} {{id: node.id}})
                    SET n += node.properties
                    """
                    
                    # Prepare batch data
                    batch_data = []
                    for node in batch:
                        props = json.loads(node['properties'])
                        props['id'] = node['node_id']
                        batch_data.append({'id': node['node_id'], 'properties': props})
                    
                    session.run(query, nodes=batch_data)
                    
                    total_loaded += len(batch)
                    print(f"  Progress: {total_loaded}/{total_count} ({100*total_loaded//total_count}%)")
            
            except Exception as e:
                print(f"  ❌ Error in batch {i//batch_size}: {str(e)}")
    
    driver.close()
    print(f"\n✅ Loaded {total_loaded} nodes")
    return total_loaded

nodes_loaded = load_nodes_to_neo4j(
    nodes_df,
    neo4j_uri,
    neo4j_username,
    neo4j_password,
    batch_size
)

# COMMAND ----------
# Load relationships to Neo4j

def load_relationships_to_neo4j(rels_df, uri, username, password, batch_size):
    """Load relationships to Neo4j in batches."""
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    # Group by relationship type
    rel_types = rels_df.select("relationship_type").distinct().collect()
    
    total_loaded = 0
    
    for row in rel_types:
        rel_type = row['relationship_type']
        type_df = rels_df.filter(F.col("relationship_type") == rel_type)
        
        total_count = type_df.count()
        print(f"\n📦 Loading {total_count} {rel_type} relationships...")
        
        # Convert to list
        rels_data = type_df.select(
            "source_node_id", "source_node_label",
            "target_node_id", "target_node_label",
            "properties"
        ).collect()
        
        # Process in batches
        for i in range(0, len(rels_data), batch_size):
            batch = rels_data[i:i+batch_size]
            
            try:
                with driver.session() as session:
                    # Prepare batch data
                    batch_data = []
                    for rel in batch:
                        props = json.loads(rel['properties'])
                        batch_data.append({
                            'source_id': rel['source_node_id'],
                            'source_label': rel['source_node_label'],
                            'target_id': rel['target_node_id'],
                            'target_label': rel['target_node_label'],
                            'properties': props
                        })
                    
                    # Use dynamic label matching
                    source_label = batch[0]['source_node_label']
                    target_label = batch[0]['target_node_label']
                    
                    query = f"""
                    UNWIND $rels AS rel
                    MATCH (source:{source_label} {{id: rel.source_id}})
                    MATCH (target:{target_label} {{id: rel.target_id}})
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET r += rel.properties
                    """
                    
                    session.run(query, rels=batch_data)
                    
                    total_loaded += len(batch)
                    print(f"  Progress: {total_loaded}/{total_count} ({100*total_loaded//total_count}%)")
            
            except Exception as e:
                print(f"  ❌ Error in batch {i//batch_size}: {str(e)}")
    
    driver.close()
    print(f"\n✅ Loaded {total_loaded} relationships")
    return total_loaded

relationships_loaded = load_relationships_to_neo4j(
    relationships_df,
    neo4j_uri,
    neo4j_username,
    neo4j_password,
    batch_size
)

# COMMAND ----------
# Verify load in Neo4j

def verify_neo4j_load(uri, username, password):
    """Verify data in Neo4j."""
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    try:
        with driver.session() as session:
            # Count nodes
            result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count")
            print("\n📊 Node counts in Neo4j:")
            for record in result:
                print(f"  {record['label']}: {record['count']}")
            
            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count")
            print("\n📊 Relationship counts in Neo4j:")
            for record in result:
                print(f"  {record['type']}: {record['count']}")
        
        driver.close()
    
    except Exception as e:
        print(f"❌ Error verifying: {str(e)}")
        driver.close()

verify_neo4j_load(neo4j_uri, neo4j_username, neo4j_password)

# COMMAND ----------
# Summary and Exit

summary = {
    'nodes_loaded': nodes_loaded,
    'relationships_loaded': relationships_loaded,
    'neo4j_uri': neo4j_uri
}

print("\n" + "="*60)
print("LOADING SUMMARY")
print("="*60)
print(f"Neo4j URI: {neo4j_uri}")
print(f"Nodes Loaded: {summary['nodes_loaded']}")
print(f"Relationships Loaded: {summary['relationships_loaded']}")
print(f"\n✅ Data successfully loaded to Neo4j Aura")

dbutils.notebook.exit(f"SUCCESS: Loaded {summary['nodes_loaded']} nodes and {summary['relationships_loaded']} relationships to Neo4j")
