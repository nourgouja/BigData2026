# Gaza YouTube Analytics - Hadoop Cluster Dockerfile
# Base image: razer99/hadoop-cluster-mouin-boubakri
# 6-node cluster: 1 NameNode, 1 SecondaryNameNode, 4 DataNodes

FROM razer99/hadoop-cluster-mouin-boubakri:latest

LABEL maintainer="Mouin Boubakri <mouin@example.com>"
LABEL description="Hadoop 3.x cluster for Gaza YouTube Analytics - Big Data Project"
LABEL version="1.0"

# Set environment variables
ENV HADOOP_HOME=/opt/hadoop
ENV HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
ENV PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV HDFS_NAMENODE_USER=root
ENV HDFS_DATANODE_USER=root
ENV HDFS_SECONDARYNAMENODE_USER=root
ENV YARN_RESOURCEMANAGER_USER=root
ENV YARN_NODEMANAGER_USER=root

# Create necessary directories
RUN mkdir -p /hadoop/dfs/name && \
    mkdir -p /hadoop/dfs/data && \
    mkdir -p /hadoop/dfs/namesecondary && \
    mkdir -p /opt/hadoop/logs && \
    chmod -R 755 /hadoop && \
    chmod -R 755 /opt/hadoop/logs

# Install additional dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    netcat \
    vim \
    less \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY hadoop-configs/*.xml $HADOOP_CONF_DIR/

# Copy startup script
COPY start-hadoop.sh /start-hadoop.sh
RUN chmod +x /start-hadoop.sh

# Expose Hadoop ports
# NameNode
EXPOSE 9870 9000 8020
# SecondaryNameNode
EXPOSE 9868 50090
# DataNode
EXPOSE 9864 9866 9867
# ResourceManager
EXPOSE 8088 8030 8031 8032 8033
# NodeManager
EXPOSE 8042 13562

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9870 || exit 1

# Default command
CMD ["/bin/bash", "/start-hadoop.sh"]
