#!/usr/bin/env python3
"""
PySpark Gaza YouTube Analytics - Hadoop Cluster Processing
Input: hdfs://localhost:9000/raw/youtube/gaza_videos.jsonl
Output: /processed/gaza_analytics/*.parquet & *.csv
"""

import sys
import re
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, udf, explode, split, lower, regexp_replace, 
    to_date, year, month, weekofyear, count, sum as _sum, 
    avg, desc, when, lit, size, array_distinct, concat_ws,
    floor, round as spark_round, coalesce
)
from pyspark.sql.types import (
    StringType, FloatType, IntegerType, ArrayType, StructType, StructField
)
from pyspark.ml.feature import HashingTF, IDF, Tokenizer, StopWordsRemover

# NLTK/VADER Setup (with error handling)
try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    
    # Download required NLTK data
    nltk.download('vader_lexicon', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
    
    # Initialize VADER
    sia = SentimentIntensityAnalyzer()
    NLTK_AVAILABLE = True
    print("✅ NLTK/VADER initialized successfully")
except Exception as e:
    print(f"⚠️  NLTK import warning: {e}")
    print("📦 Installing NLTK... Run: pip install nltk vaderSentiment")
    NLTK_AVAILABLE = False

# ============================================================================
# CONFIGURATION
# ============================================================================
HDFS_INPUT = "hdfs://localhost:9000/raw/youtube/gaza_videos.jsonl"
HDFS_OUTPUT_BASE = "hdfs://localhost:9000/processed/gaza_analytics"
LOCAL_OUTPUT_BASE = "/processed/gaza_analytics"  # Fallback for local mode

# Date range for temporal analysis
START_DATE = "2023-10-07"  # Gaza conflict start
VIRAL_THRESHOLD = 1000000  # 1M views

# ============================================================================
# SPARK SESSION INITIALIZATION
# ============================================================================
def create_spark_session():
    """Initialize Spark session with optimized configs for Hadoop cluster"""
    return SparkSession.builder \
        .appName("Gaza_YouTube_Analytics_PySpark") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.shuffle.partitions", "200") \
        .config("spark.executor.memory", "4g") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()

# ============================================================================
# UDFs FOR NLP PROCESSING
# ============================================================================
def get_sentiment_score(text):
    """VADER sentiment analysis UDF - returns compound score [-1, 1]"""
    if not text or not NLTK_AVAILABLE:
        return 0.0
    try:
        scores = sia.polarity_scores(str(text))
        return float(scores['compound'])
    except:
        return 0.0

def get_sentiment_label(score):
    """Convert sentiment score to label"""
    if score >= 0.05:
        return "positive"
    elif score <= -0.05:
        return "negative"
    else:
        return "neutral"

def clean_tokenize(text):
    """Clean and tokenize text for keyword extraction"""
    if not text:
        return []
    try:
        # Remove URLs, mentions, special chars
        text = str(text).lower()
        text = re.sub(r'http\S+|www\S+|@\w+|#\w+', '', text)
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Tokenize and filter
        tokens = text.split()
        # Filter short words and common stopwords
        stopwords_set = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                        'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was',
                        'gaza', 'video', 'palestine', 'israel', 'war', 'news'}
        tokens = [t for t in tokens if len(t) > 3 and t not in stopwords_set]
        return tokens[:100]  # Limit to top 100 tokens per document
    except:
        return []

# Register UDFs
sentiment_score_udf = udf(get_sentiment_score, FloatType())
sentiment_label_udf = udf(get_sentiment_label, StringType())
tokenize_udf = udf(clean_tokenize, ArrayType(StringType()))

# ============================================================================
# MAIN PROCESSING PIPELINE
# ============================================================================
def main():
    print("=" * 80)
    print("🚀 GAZA YOUTUBE ANALYTICS - PYSPARK HADOOP CLUSTER")
    print("=" * 80)
    
    # Initialize Spark
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # ====================================================================
        # STEP 1: LOAD DATA FROM HDFS
        # ====================================================================
        print(f"\n📂 STEP 1: Loading data from {HDFS_INPUT}")
        
        # Try HDFS first, fallback to local
        try:
            df_raw = spark.read \
                .option("multiLine", "true") \
                .option("inferSchema", "true") \
                .json(HDFS_INPUT)
            output_base = HDFS_OUTPUT_BASE
            print(f"✅ Loaded from HDFS: {df_raw.count()} records")
        except Exception as e:
            print(f"⚠️  HDFS read failed: {e}")
            print("🔄 Trying local file: gaza_videos.json")
            df_raw = spark.read \
                .option("multiLine", "true") \
                .option("inferSchema", "true") \
                .json("gaza_videos.json")
            output_base = LOCAL_OUTPUT_BASE
            print(f"✅ Loaded from local: {df_raw.count()} records")
        
        print(f"📊 Schema:")
        df_raw.printSchema()
        
        # ====================================================================
        # STEP 2: DATA CLEANING & FEATURE ENGINEERING
        # ====================================================================
        print("\n🧹 STEP 2: Data Cleaning & Feature Engineering")
        
        # Drop rows with critical nulls
        df_clean = df_raw.dropna(subset=["video_id", "title", "view_count"])
        
        # Parse published_at to date
        df_clean = df_clean.withColumn(
            "published_date",
            to_date(col("published_at"))
        )
        
        # Cast numeric columns with nulls handling
        df_clean = df_clean \
            .withColumn("views", coalesce(col("view_count"), lit(0)).cast(IntegerType())) \
            .withColumn("likes", coalesce(col("like_count"), lit(0)).cast(IntegerType())) \
            .withColumn("comments", coalesce(col("comment_count"), lit(0)).cast(IntegerType()))
        
        # Calculate engagement rate: (views / (likes + comments + 1)) * 100
        df_clean = df_clean.withColumn(
            "engagement",
            spark_round(
                (col("views") / (col("likes") + col("comments") + lit(1))) * 100,
                2
            )
        )
        
        # Add temporal features
        df_clean = df_clean \
            .withColumn("year", year(col("published_date"))) \
            .withColumn("month", month(col("published_date"))) \
            .withColumn("week", weekofyear(col("published_date")))
        
        # Flag viral videos
        df_clean = df_clean.withColumn(
            "is_viral",
            when(col("views") >= VIRAL_THRESHOLD, 1).otherwise(0)
        )
        
        # Cache cleaned data
        df_clean.cache()
        
        print(f"✅ Cleaned: {df_clean.count()} videos")
        print(f"📊 Date range: {df_clean.agg({'published_date': 'min'}).collect()[0][0]} to {df_clean.agg({'published_date': 'max'}).collect()[0][0]}")
        
        # ====================================================================
        # STEP 3: NLP - SENTIMENT ANALYSIS & KEYWORD EXTRACTION
        # ====================================================================
        print("\n🔤 STEP 3: NLP Processing - Sentiment Analysis & Keywords")
        
        # Sentiment analysis on titles
        df_sentiment = df_clean.withColumn(
            "sentiment_score",
            sentiment_score_udf(col("title"))
        ).withColumn(
            "sentiment_label",
            sentiment_label_udf(col("sentiment_score"))
        )
        
        # Tokenize titles for keyword extraction
        df_sentiment = df_sentiment.withColumn(
            "tokens",
            tokenize_udf(concat_ws(" ", col("title"), coalesce(col("description"), lit(""))))
        )
        
        # Filter out empty token arrays
        df_tokens = df_sentiment.filter(size(col("tokens")) > 0)
        
        print(f"✅ Sentiment analysis completed on {df_sentiment.count()} videos")
        
        # TF-IDF for top keywords
        print("📊 Extracting top 50 keywords using TF-IDF...")
        
        # Flatten tokens for word frequency
        df_words = df_tokens.select(explode(col("tokens")).alias("word"))
        word_counts = df_words.groupBy("word").count() \
            .orderBy(desc("count")) \
            .limit(50)
        
        print("\n🔝 TOP 50 KEYWORDS:")
        word_counts.show(50, truncate=False)
        
        # Channel-level sentiment aggregation
        df_channel_sentiment = df_sentiment.groupBy("channel") \
            .agg(
                count("*").alias("video_count"),
                avg("sentiment_score").alias("avg_sentiment"),
                _sum(when(col("sentiment_label") == "positive", 1).otherwise(0)).alias("positive_count"),
                _sum(when(col("sentiment_label") == "negative", 1).otherwise(0)).alias("negative_count"),
                _sum(when(col("sentiment_label") == "neutral", 1).otherwise(0)).alias("neutral_count")
            ) \
            .orderBy(desc("video_count"))
        
        # ====================================================================
        # STEP 4: AGGREGATIONS
        # ====================================================================
        print("\n📈 STEP 4: Computing Aggregations")
        
        # 4.1: Top 10 channels by engagement
        df_top_channels = df_clean.groupBy("channel") \
            .agg(
                count("*").alias("total_videos"),
                _sum("views").alias("total_views"),
                _sum("likes").alias("total_likes"),
                _sum("comments").alias("total_comments"),
                avg("engagement").alias("avg_engagement")
            ) \
            .withColumn(
                "engagement_rate",
                spark_round(
                    (col("total_likes") + col("total_comments")) / col("total_views") * 100,
                    2
                )
            ) \
            .orderBy(desc("avg_engagement")) \
            .limit(10)
        
        print("\n🏆 TOP 10 CHANNELS BY ENGAGEMENT:")
        df_top_channels.show(10, truncate=False)
        
        # 4.2: Temporal trends (views per week since Oct 2023)
        df_trends = df_clean.filter(col("published_date") >= START_DATE) \
            .groupBy("year", "week") \
            .agg(
                count("*").alias("videos_count"),
                _sum("views").alias("total_views"),
                _sum("likes").alias("total_likes"),
                avg("engagement").alias("avg_engagement")
            ) \
            .orderBy("year", "week")
        
        print(f"\n📅 TEMPORAL TRENDS (since {START_DATE}):")
        df_trends.show(20, truncate=False)
        
        # 4.3: Viral videos (>1M views) analysis
        df_viral = df_clean.filter(col("is_viral") == 1) \
            .select("video_id", "title", "channel", "views", "likes", 
                   "comments", "engagement", "published_date") \
            .orderBy(desc("views"))
        
        viral_count = df_viral.count()
        print(f"\n🔥 VIRAL VIDEOS (>{VIRAL_THRESHOLD:,} views): {viral_count} videos")
        df_viral.show(10, truncate=False)
        
        # ====================================================================
        # STEP 5: SAVE RESULTS
        # ====================================================================
        print("\n💾 STEP 5: Saving Results to HDFS/Local")
        
        # Save top channels as Parquet
        output_channels = f"{output_base}/df_top_channels.parquet"
        df_top_channels.coalesce(1).write.mode("overwrite").parquet(output_channels)
        print(f"✅ Saved: {output_channels}")
        
        # Save trends as CSV
        output_trends = f"{output_base}/df_trends.csv"
        df_trends.coalesce(1).write.mode("overwrite") \
            .option("header", "true").csv(output_trends)
        print(f"✅ Saved: {output_trends}")
        
        # Save sentiment analysis as Parquet
        output_sentiment = f"{output_base}/df_sentiment.parquet"
        df_sentiment.select(
            "video_id", "title", "channel", "views", "likes", "comments",
            "sentiment_score", "sentiment_label", "published_date", "engagement"
        ).coalesce(10).write.mode("overwrite").parquet(output_sentiment)
        print(f"✅ Saved: {output_sentiment}")
        
        # Save viral videos as CSV
        output_viral = f"{output_base}/df_viral.csv"
        df_viral.coalesce(1).write.mode("overwrite") \
            .option("header", "true").csv(output_viral)
        print(f"✅ Saved: {output_viral}")
        
        # Save keywords as CSV
        output_keywords = f"{output_base}/df_keywords.csv"
        word_counts.coalesce(1).write.mode("overwrite") \
            .option("header", "true").csv(output_keywords)
        print(f"✅ Saved: {output_keywords}")
        
        # Save channel sentiment as Parquet
        output_channel_sentiment = f"{output_base}/df_channel_sentiment.parquet"
        df_channel_sentiment.coalesce(1).write.mode("overwrite") \
            .parquet(output_channel_sentiment)
        print(f"✅ Saved: {output_channel_sentiment}")
        
        # Display final sentiment results
        print("\n" + "=" * 80)
        print("📊 SENTIMENT ANALYSIS RESULTS (Sample 20)")
        print("=" * 80)
        df_sentiment.select(
            "title", "channel", "views", "sentiment_score", "sentiment_label"
        ).orderBy(desc("views")).show(20, truncate=False)
        
        # ====================================================================
        # FINAL STATISTICS
        # ====================================================================
        print("\n" + "=" * 80)
        print("📈 FINAL STATISTICS SUMMARY")
        print("=" * 80)
        
        total_videos = df_clean.count()
        total_views = df_clean.agg(_sum("views")).collect()[0][0]
        avg_views = df_clean.agg(avg("views")).collect()[0][0]
        
        sentiment_dist = df_sentiment.groupBy("sentiment_label").count().collect()
        sentiment_dict = {row['sentiment_label']: row['count'] for row in sentiment_dist}
        
        print(f"📹 Total Videos Analyzed: {total_videos:,}")
        print(f"👁️  Total Views: {total_views:,}")
        print(f"📊 Average Views per Video: {avg_views:,.0f}")
        print(f"🔥 Viral Videos (>1M): {viral_count:,}")
        print(f"\n😊 Positive Sentiment: {sentiment_dict.get('positive', 0):,}")
        print(f"😐 Neutral Sentiment: {sentiment_dict.get('neutral', 0):,}")
        print(f"😞 Negative Sentiment: {sentiment_dict.get('negative', 0):,}")
        
        print("\n" + "=" * 80)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        spark.stop()

# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║  GAZA YOUTUBE ANALYTICS - PYSPARK HADOOP CLUSTER               ║
    ║  Author: PySpark Gaza Analytics Team                            ║
    ║  Input: HDFS /raw/youtube/gaza_videos.jsonl                     ║
    ║  Output: HDFS /processed/gaza_analytics/*.parquet & *.csv       ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Check NLTK installation
    if not NLTK_AVAILABLE:
        print("\n⚠️  WARNING: NLTK not available. Install with:")
        print("   pip install nltk vaderSentiment")
        print("   Continuing with limited NLP features...\n")
    
    main()
