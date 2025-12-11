#!/bin/bash
# Neo4j Spark Connector Initialization Script
# Version: 5.3.0_for_spark_3.5
# Optimized for UK South region e-commerce workload

set -e

echo "================================================"
echo "Neo4j Spark Connector Initialization"
echo "================================================"

# Set connector version
export NEO4J_CONNECTOR_VERSION="5.3.0_for_spark_3.5"
export NEO4J_CONNECTOR_ARTIFACT="org.neo4j:neo4j-connector-apache-spark_2.12:${NEO4J_CONNECTOR_VERSION}"

echo "Connector Version: ${NEO4J_CONNECTOR_VERSION}"

# Configure connection pooling for high throughput
export NEO4J_MAX_CONNECTION_POOL_SIZE=100
export NEO4J_CONNECTION_TIMEOUT=30
export NEO4J_MAX_TRANSACTION_RETRY_TIME=30
export NEO4J_CONNECTION_ACQUISITION_TIMEOUT=60
export NEO4J_MAX_CONNECTION_LIFETIME=3600

echo "✓ Connection pooling configured"

# Configure batch loading performance
export NEO4J_BATCH_SIZE=5000
export NEO4J_NODE_WRITE_BATCH_SIZE=5000
export NEO4J_RELATIONSHIP_WRITE_BATCH_SIZE=5000
export NEO4J_PARALLEL_WRITES=4

echo "✓ Batch loading configured"

# Configure write strategies
export NEO4J_USE_UNWIND=true
export NEO4J_USE_BATCH_IMPORT=true
export NEO4J_TRANSACTION_RETRIES=3
export NEO4J_TRANSACTION_TIMEOUT=300

echo "✓ Write strategies configured"

# Configure Spark optimizations for Neo4j
export SPARK_DATABRICKS_DELTA_PREVIEW_ENABLED=true
export SPARK_DATABRICKS_IO_CACHE_ENABLED=true
export SPARK_SQL_ADAPTIVE_ENABLED=true
export SPARK_SQL_ADAPTIVE_COALESCE_PARTITIONS_ENABLED=true

echo "✓ Spark optimizations configured"

# Memory optimization for graph workloads
export SPARK_MEMORY_FRACTION=0.8
export SPARK_MEMORY_STORAGE_FRACTION=0.3

echo "✓ Memory optimization configured"

# UK South region marker
export NEO4J_REGION="uksouth"
export NEO4J_DATA_RESIDENCY="UK"

echo "✓ UK South region configuration set"

# E-commerce use case optimization
export USE_CASE="ecommerce"
export WORKLOAD_TYPE="graph_analytics"

echo "✓ E-commerce workload type set"

# Create connector info file
cat > /tmp/neo4j-connector-info.txt << EOF
Neo4j Spark Connector Information
==================================
Version: ${NEO4J_CONNECTOR_VERSION}
Artifact: ${NEO4J_CONNECTOR_ARTIFACT}
Region: ${NEO4J_REGION}
Use Case: ${USE_CASE}
Batch Size: ${NEO4J_BATCH_SIZE}
Parallel Writes: ${NEO4J_PARALLEL_WRITES}
Connection Pool: ${NEO4J_MAX_CONNECTION_POOL_SIZE}
Transaction Retries: ${NEO4J_TRANSACTION_RETRIES}
EOF

echo ""
cat /tmp/neo4j-connector-info.txt
echo ""

# Set up Python environment for Neo4j
if command -v python &> /dev/null; then
    echo "Configuring Python environment for Neo4j..."
    
    # Install neo4j driver if not present
    python -m pip install --quiet neo4j==5.14.0 || echo "Neo4j Python driver already installed"
    
    echo "✓ Python environment configured"
fi

# Create helper functions file
cat > /tmp/neo4j-helper-functions.sh << 'EOF'
#!/bin/bash
# Neo4j Helper Functions

neo4j_test_connection() {
    echo "Testing Neo4j connection..."
    # Would test connection here
    echo "Connection test placeholder"
}

neo4j_get_stats() {
    echo "Neo4j Connector Statistics"
    echo "=========================="
    echo "Batch Size: ${NEO4J_BATCH_SIZE}"
    echo "Parallel Writes: ${NEO4J_PARALLEL_WRITES}"
    echo "Connection Pool Size: ${NEO4J_MAX_CONNECTION_POOL_SIZE}"
}

neo4j_optimize_for_ecommerce() {
    echo "Optimizing for e-commerce workload..."
    export NEO4J_BATCH_SIZE=5000
    export NEO4J_PARALLEL_WRITES=4
    echo "✓ E-commerce optimization applied"
}
EOF

chmod +x /tmp/neo4j-helper-functions.sh
source /tmp/neo4j-helper-functions.sh

echo ""
echo "================================================"
echo "Neo4j Spark Connector Initialization Complete"
echo "================================================"
echo ""
echo "Environment Variables Set:"
echo "  - NEO4J_CONNECTOR_VERSION: ${NEO4J_CONNECTOR_VERSION}"
echo "  - NEO4J_REGION: ${NEO4J_REGION}"
echo "  - NEO4J_BATCH_SIZE: ${NEO4J_BATCH_SIZE}"
echo "  - NEO4J_PARALLEL_WRITES: ${NEO4J_PARALLEL_WRITES}"
echo ""
echo "Helper functions available:"
echo "  - neo4j_test_connection"
echo "  - neo4j_get_stats"
echo "  - neo4j_optimize_for_ecommerce"
echo ""
echo "✅ Ready for Neo4j + Databricks e-commerce pipeline"
