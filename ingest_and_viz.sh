#!/bin/bash
###############################################################################
# Gaza YouTube Analytics - Hadoop Docker Pipeline
# Author: Hadoop Gaza Analytics Team
# Description: End-to-end data ingestion, processing, and export
###############################################################################

set -e  # Exit on error

# Configuration
CONTAINER_NAME="namenode"  # NameNode container from docker-compose
SPARK_CONTAINER="spark-master"  # Spark Master container from docker-compose
INPUT_FILE="gaza_videos.json"
JSONL_FILE="gaza_videos.jsonl"
HDFS_INPUT_PATH="/raw/youtube"
HDFS_OUTPUT_PATH="/processed/gaza_analytics"
LOCAL_OUTPUT_DIR="./hdfs_results"

# Verify cluster is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ ERROR: Hadoop cluster is not running!"
    echo "   Please start the cluster first with:"
    echo "   docker compose up -d"
    exit 1
fi

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         GAZA YOUTUBE ANALYTICS - HADOOP PIPELINE               ║"
echo "║              Data Ingestion & Visualization                     ║"
echo "╚══════════════════════════════════════════════════════════════════╝"

# ============================================================================
# STEP 1: Convert JSON to JSONL
# ============================================================================
echo ""
echo "📋 STEP 1: Converting JSON to JSONL format..."

if [ -f "$INPUT_FILE" ]; then
    python3 << 'PYTHON_EOF'
import json
import sys

input_files = ["gaza_videos.json", "gaza_full_575.json", "gaza_sample.json"]
input_file = None

for f in input_files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            videos = json.load(file)
            input_file = f
            break
    except FileNotFoundError:
        continue
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON decode error in {f}: {e}")
        continue

if not input_file:
    print("❌ No valid Gaza videos JSON file found!")
    sys.exit(1)

print(f"✅ Using input file: {input_file}")
print(f"📊 Found {len(videos)} videos")

# Write as JSONL
with open('gaza_videos.jsonl', 'w', encoding='utf-8') as f:
    for video in videos:
        f.write(json.dumps(video, ensure_ascii=False) + '\n')

print(f"✅ Converted to JSONL: gaza_videos.jsonl ({len(videos)} records)")
PYTHON_EOF

    if [ $? -ne 0 ]; then
        echo "❌ JSON to JSONL conversion failed!"
        exit 1
    fi
else
    echo "❌ Input file not found: $INPUT_FILE"
    echo "Available files:"
    ls -lh gaza*.json 2>/dev/null || echo "No gaza JSON files found"
    exit 1
fi

# ============================================================================
# STEP 2: Copy JSONL to Hadoop Container
# ============================================================================
echo ""
echo "🐳 STEP 2: Copying JSONL to Hadoop container..."

# Check if container exists
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "⚠️  Container '$CONTAINER_NAME' not found or not running!"
    echo "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}"
    echo ""
    echo "💡 Tip: Update CONTAINER_NAME variable in script to match your Hadoop container"
    exit 1
fi

docker cp $JSONL_FILE $CONTAINER_NAME:/tmp/
echo "✅ Copied $JSONL_FILE to $CONTAINER_NAME:/tmp/"

# ============================================================================
# STEP 3: Create HDFS Directories
# ============================================================================
echo ""
echo "📁 STEP 3: Creating HDFS directories..."

docker exec $CONTAINER_NAME hdfs dfs -mkdir -p $HDFS_INPUT_PATH || true
docker exec $CONTAINER_NAME hdfs dfs -mkdir -p $HDFS_OUTPUT_PATH || true

echo "✅ Created HDFS directories:"
echo "   - $HDFS_INPUT_PATH"
echo "   - $HDFS_OUTPUT_PATH"

# ============================================================================
# STEP 4: Upload to HDFS
# ============================================================================
echo ""
echo "📤 STEP 4: Uploading JSONL to HDFS..."

docker exec $CONTAINER_NAME hdfs dfs -put -f /tmp/$JSONL_FILE $HDFS_INPUT_PATH/

echo "✅ Uploaded to HDFS: $HDFS_INPUT_PATH/$JSONL_FILE"

# Verify upload
echo ""
echo "🔍 Verifying HDFS upload..."
docker exec $CONTAINER_NAME hdfs dfs -ls $HDFS_INPUT_PATH/

FILE_SIZE=$(docker exec $CONTAINER_NAME hdfs dfs -du -h $HDFS_INPUT_PATH/$JSONL_FILE | awk '{print $1}')
echo "📊 File size in HDFS: $FILE_SIZE"

# ============================================================================
# STEP 5: Copy PySpark Script to Spark Container
# ============================================================================
echo ""
echo "🔥 STEP 5: Preparing PySpark environment..."

if docker ps | grep -q "$SPARK_CONTAINER"; then
    # Copy PySpark script
    docker cp pyspark_gaza.py $SPARK_CONTAINER:/opt/pyspark_gaza.py
    echo "✅ Copied pyspark_gaza.py to Spark container"
    
    # Install dependencies
    echo "📦 Installing NLTK and dependencies..."
    docker exec $SPARK_CONTAINER pip install -q nltk vaderSentiment 2>/dev/null || echo "⚠️  NLTK install warning (may already be installed)"
    
    echo "✅ PySpark environment ready"
else
    echo "⚠️  Spark container '$SPARK_CONTAINER' not found. Skipping PySpark setup."
    echo "💡 Tip: Update SPARK_CONTAINER variable or run PySpark manually"
fi

# ============================================================================
# STEP 6: Run PySpark Job
# ============================================================================
echo ""
echo "⚡ STEP 6: Running PySpark analytics job..."
echo "This may take 2-5 minutes depending on data size..."
echo ""

if docker ps | grep -q "$SPARK_CONTAINER"; then
    docker exec -it $SPARK_CONTAINER spark-submit \
        --master local[*] \
        --driver-memory 2g \
        --executor-memory 4g \
        /opt/pyspark_gaza.py
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ PySpark job completed successfully!"
    else
        echo ""
        echo "❌ PySpark job failed! Check logs above for errors."
        exit 1
    fi
else
    echo "⚠️  Skipping PySpark execution (Spark container not available)"
fi

# ============================================================================
# STEP 7: Download Results from HDFS
# ============================================================================
echo ""
echo "📥 STEP 7: Downloading results from HDFS..."

# Create local output directory
mkdir -p $LOCAL_OUTPUT_DIR

# Download all output files
echo "Downloading Parquet and CSV files..."

# Download each output file type
docker exec $CONTAINER_NAME hdfs dfs -get $HDFS_OUTPUT_PATH/df_top_channels.parquet /tmp/ 2>/dev/null || true
docker exec $CONTAINER_NAME hdfs dfs -get $HDFS_OUTPUT_PATH/df_trends.csv /tmp/ 2>/dev/null || true
docker exec $CONTAINER_NAME hdfs dfs -get $HDFS_OUTPUT_PATH/df_sentiment.parquet /tmp/ 2>/dev/null || true
docker exec $CONTAINER_NAME hdfs dfs -get $HDFS_OUTPUT_PATH/df_viral.csv /tmp/ 2>/dev/null || true
docker exec $CONTAINER_NAME hdfs dfs -get $HDFS_OUTPUT_PATH/df_keywords.csv /tmp/ 2>/dev/null || true
docker exec $CONTAINER_NAME hdfs dfs -get $HDFS_OUTPUT_PATH/df_channel_sentiment.parquet /tmp/ 2>/dev/null || true

# Copy from container to local
docker cp $CONTAINER_NAME:/tmp/df_top_channels.parquet $LOCAL_OUTPUT_DIR/ 2>/dev/null || true
docker cp $CONTAINER_NAME:/tmp/df_trends.csv $LOCAL_OUTPUT_DIR/ 2>/dev/null || true
docker cp $CONTAINER_NAME:/tmp/df_sentiment.parquet $LOCAL_OUTPUT_DIR/ 2>/dev/null || true
docker cp $CONTAINER_NAME:/tmp/df_viral.csv $LOCAL_OUTPUT_DIR/ 2>/dev/null || true
docker cp $CONTAINER_NAME:/tmp/df_keywords.csv $LOCAL_OUTPUT_DIR/ 2>/dev/null || true
docker cp $CONTAINER_NAME:/tmp/df_channel_sentiment.parquet $LOCAL_OUTPUT_DIR/ 2>/dev/null || true

echo ""
echo "✅ Results downloaded to: $LOCAL_OUTPUT_DIR"
echo ""
echo "📂 Downloaded files:"
ls -lh $LOCAL_OUTPUT_DIR/ 2>/dev/null || echo "⚠️  No files downloaded (check HDFS output path)"

# ============================================================================
# STEP 8: Convert Parquet to CSV for Easy Viewing
# ============================================================================
echo ""
echo "🔄 STEP 8: Converting Parquet files to CSV..."

python3 << 'CONVERT_EOF'
import os
import glob

try:
    import pandas as pd
    
    output_dir = "./hdfs_results"
    
    # Find all parquet directories
    parquet_dirs = glob.glob(f"{output_dir}/*.parquet")
    
    for parquet_dir in parquet_dirs:
        try:
            # Read parquet
            df = pd.read_parquet(parquet_dir)
            
            # Generate CSV filename
            csv_file = parquet_dir.replace('.parquet', '.csv')
            
            # Save as CSV
            df.to_csv(csv_file, index=False)
            print(f"✅ Converted: {os.path.basename(parquet_dir)} → {os.path.basename(csv_file)} ({len(df)} rows)")
        except Exception as e:
            print(f"⚠️  Failed to convert {parquet_dir}: {e}")
    
    print("\n📊 All conversions complete!")
    
except ImportError:
    print("⚠️  Pandas not installed. Skipping Parquet to CSV conversion.")
    print("   Install with: pip install pandas pyarrow")
except Exception as e:
    print(f"⚠️  Conversion error: {e}")
CONVERT_EOF

# ============================================================================
# STEP 9: Summary & Next Steps
# ============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    PIPELINE COMPLETE! ✅                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 SUMMARY:"
echo "   ✓ Data ingested to HDFS: $HDFS_INPUT_PATH/$JSONL_FILE"
echo "   ✓ PySpark analytics completed"
echo "   ✓ Results downloaded to: $LOCAL_OUTPUT_DIR"
echo ""
echo "📂 OUTPUT FILES:"
ls -lh $LOCAL_OUTPUT_DIR/*.csv 2>/dev/null | awk '{print "   " $0}'
echo ""
echo "🌐 HDFS WEB UI:"
echo "   Browse files: http://localhost:9870/explorer.html#$HDFS_OUTPUT_PATH"
echo ""
echo "📓 NEXT STEPS:"
echo "   1. Open gaza_dashboard.ipynb in Jupyter"
echo "   2. Run all cells to generate visualizations"
echo "   3. View HDFS UI screenshots at http://localhost:9870"
echo ""
echo "🚀 Launch Jupyter:"
echo "   jupyter notebook gaza_dashboard.ipynb"
echo ""
