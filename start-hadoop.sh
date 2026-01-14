#!/bin/bash
###############################################################################
# Hadoop Cluster Role-based Initialization Script
# Author: Mouin Boubakri
# Description: Starts Hadoop services based on HADOOP_ROLE environment variable
###############################################################################

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     Hadoop Cluster Initialization - Gaza YouTube Analytics     ║"
echo "╚══════════════════════════════════════════════════════════════════╝"

# Get role from environment variable
ROLE=${HADOOP_ROLE:-namenode}
CLUSTER_NAME=${CLUSTER_NAME:-gaza-youtube-analytics}

echo "🔧 Starting Hadoop cluster node..."
echo "   Role: $ROLE"
echo "   Cluster: $CLUSTER_NAME"
echo "   Hostname: $(hostname)"
echo ""

# Hadoop paths
HADOOP_HOME=${HADOOP_HOME:-/opt/hadoop}
HDFS_NAMENODE_DIR=${HDFS_NAMENODE_DIR:-/hadoop/dfs/name}
HDFS_DATANODE_DIR=${HDFS_DATANODE_DIR:-/hadoop/dfs/data}
HDFS_SECONDARY_DIR=${HDFS_SECONDARY_DIR:-/hadoop/dfs/namesecondary}

# Ensure directories exist
mkdir -p $HDFS_NAMENODE_DIR
mkdir -p $HDFS_DATANODE_DIR
mkdir -p $HDFS_SECONDARY_DIR
mkdir -p $HADOOP_HOME/logs

# Set permissions
chmod -R 755 /hadoop
chmod -R 755 $HADOOP_HOME/logs

###############################################################################
# NAMENODE INITIALIZATION
###############################################################################
if [ "$ROLE" = "namenode" ]; then
    echo "🏛️  Initializing NameNode..."
    
    # Check if NameNode is already formatted
    if [ ! -f "$HDFS_NAMENODE_DIR/current/VERSION" ]; then
        echo "📝 Formatting HDFS NameNode (first time only)..."
        $HADOOP_HOME/bin/hdfs namenode -format -force -clusterID $CLUSTER_NAME
        echo "✅ NameNode formatted successfully"
    else
        echo "✓ NameNode already formatted, skipping format"
    fi
    
    # Start NameNode
    echo "🚀 Starting HDFS NameNode..."
    $HADOOP_HOME/bin/hdfs --daemon start namenode
    
    # Wait for NameNode to be ready
    echo "⏳ Waiting for NameNode to start..."
    for i in {1..30}; do
        if curl -s http://localhost:9870 > /dev/null 2>&1; then
            echo "✅ NameNode is ready!"
            break
        fi
        echo "   Attempt $i/30: NameNode not ready yet..."
        sleep 2
    done
    
    # Start ResourceManager (YARN)
    echo "🚀 Starting YARN ResourceManager..."
    $HADOOP_HOME/bin/yarn --daemon start resourcemanager
    
    # Wait for ResourceManager
    echo "⏳ Waiting for ResourceManager to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8088 > /dev/null 2>&1; then
            echo "✅ ResourceManager is ready!"
            break
        fi
        echo "   Attempt $i/30: ResourceManager not ready yet..."
        sleep 2
    done
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                    NAMENODE STARTED SUCCESSFULLY                ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo "🌐 HDFS NameNode UI: http://$(hostname -i):9870"
    echo "🌐 YARN ResourceManager UI: http://$(hostname -i):8088"
    echo ""

###############################################################################
# SECONDARY NAMENODE INITIALIZATION
###############################################################################
elif [ "$ROLE" = "secondarynamenode" ]; then
    echo "🔄 Initializing Secondary NameNode..."
    
    # Wait for NameNode to be available
    echo "⏳ Waiting for NameNode to be available..."
    while ! nc -z namenode 9870; do
        echo "   Waiting for NameNode..."
        sleep 3
    done
    echo "✅ NameNode is available"
    
    # Start Secondary NameNode
    echo "🚀 Starting HDFS Secondary NameNode..."
    $HADOOP_HOME/bin/hdfs --daemon start secondarynamenode
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║            SECONDARY NAMENODE STARTED SUCCESSFULLY              ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo "🌐 Secondary NameNode UI: http://$(hostname -i):9868"
    echo ""

###############################################################################
# DATANODE INITIALIZATION
###############################################################################
elif [ "$ROLE" = "datanode" ]; then
    echo "💾 Initializing DataNode..."
    
    # Wait for NameNode to be available
    echo "⏳ Waiting for NameNode to be available..."
    while ! nc -z namenode 9870; do
        echo "   Waiting for NameNode..."
        sleep 3
    done
    echo "✅ NameNode is available"
    
    # Additional wait to ensure NameNode is fully ready
    sleep 5
    
    # Start DataNode
    echo "🚀 Starting HDFS DataNode..."
    $HADOOP_HOME/bin/hdfs --daemon start datanode
    
    # Start NodeManager (YARN)
    echo "🚀 Starting YARN NodeManager..."
    $HADOOP_HOME/bin/yarn --daemon start nodemanager
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                DATANODE STARTED SUCCESSFULLY                    ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo "🌐 DataNode UI: http://$(hostname -i):9864"
    echo ""

###############################################################################
# UNKNOWN ROLE
###############################################################################
else
    echo "❌ ERROR: Unknown HADOOP_ROLE: $ROLE"
    echo "   Valid roles: namenode, secondarynamenode, datanode"
    exit 1
fi

###############################################################################
# KEEP CONTAINER RUNNING
###############################################################################
echo "📊 Cluster node is running. Checking status..."

# Display running Java processes
echo ""
echo "🔍 Running Hadoop processes:"
jps -l

# Monitor logs
echo ""
echo "📜 Tailing logs (Ctrl+C to exit)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Tail appropriate log based on role
if [ "$ROLE" = "namenode" ]; then
    tail -f $HADOOP_HOME/logs/hadoop-*-namenode-*.log
elif [ "$ROLE" = "secondarynamenode" ]; then
    tail -f $HADOOP_HOME/logs/hadoop-*-secondarynamenode-*.log
elif [ "$ROLE" = "datanode" ]; then
    tail -f $HADOOP_HOME/logs/hadoop-*-datanode-*.log
else
    # Keep container running
    tail -f /dev/null
fi
