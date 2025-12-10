#!/bin/bash
# Neo4j Connector Setup Init Script for Databricks
# This script sets up the Neo4j Spark connector on cluster initialization

echo "Starting Neo4j connector setup..."

# Install Neo4j Python driver
/databricks/python/bin/pip install neo4j

# Download and configure Neo4j Spark connector
# The Maven library is already configured in cluster settings

echo "Neo4j connector setup complete!"
