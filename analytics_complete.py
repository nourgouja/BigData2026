#!/usr/bin/env python3
"""
Complete Analytics Pipeline for Gaza YouTube Dataset
Generates ALL PDF-required deliverables with available data fields

Available fields: video_id, title, description, channel, published_at, 
                  view_count, like_count, comment_count, duration

NOT available: tags, language (explicit), country
Workaround: Extract language hints from title/description text patterns
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
from collections import Counter
import re
from datetime import datetime
import os

# Output directory
OUTPUT_DIR = "artifacts/analytics/2026-01-16"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 80)
print("GAZA YOUTUBE ANALYTICS - COMPLETE PIPELINE")
print("=" * 80)

# ============================================================================
# STEP 1: LOAD DATA
# ============================================================================
print("\n📂 STEP 1: Loading data from gaza_videos.jsonl...")

videos = []
with open('gaza_videos.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        videos.append(json.loads(line))

df = pd.DataFrame(videos)

# Convert numeric columns
df['view_count'] = pd.to_numeric(df['view_count'], errors='coerce').fillna(0).astype(int)
df['like_count'] = pd.to_numeric(df['like_count'], errors='coerce').fillna(0).astype(int)
df['comment_count'] = pd.to_numeric(df['comment_count'], errors='coerce').fillna(0).astype(int)

# Parse date
df['published_at'] = pd.to_datetime(df['published_at'])
df['published_date'] = df['published_at'].dt.date

# Calculate engagement score
df['engagement_score'] = df['like_count'] + df['comment_count']
df['engagement_rate'] = (df['engagement_score'] / (df['view_count'] + 1)) * 100

print(f"✅ Loaded {len(df)} videos")
print(f"📊 Date range: {df['published_date'].min()} to {df['published_date'].max()}")

# ============================================================================
# STEP 2: KEYWORD EXTRACTION (from titles + descriptions)
# ============================================================================
print("\n🔤 STEP 2: Extracting keywords from titles and descriptions...")

def clean_text(text):
    """Remove URLs, mentions, hashtags, special chars"""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    # Remove URLs
    text = re.sub(r'http\S+|www\S+', '', text)
    # Remove mentions and hashtags (but keep the word)
    text = re.sub(r'[@#]', ' ', text)
    # Remove special chars except spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    return text

def extract_keywords(text, min_length=3):
    """Extract words from text"""
    text = clean_text(text)
    words = text.split()
    # Filter stopwords
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
                 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were',
                 'this', 'that', 'it', 'as', 'be', 'has', 'have', 'had', 'will',
                 'would', 'could', 'should', 'may', 'can', 'their', 'our', 'your'}
    words = [w for w in words if len(w) >= min_length and w not in stopwords]
    return words

# Extract all keywords
all_keywords = []
for idx, row in df.iterrows():
    text = str(row['title']) + ' ' + str(row['description'])
    keywords = extract_keywords(text)
    all_keywords.extend(keywords)

# Count keywords
keyword_counts = Counter(all_keywords)
top_keywords = keyword_counts.most_common(50)

# Save top keywords
df_keywords = pd.DataFrame(top_keywords, columns=['keyword', 'frequency'])
df_keywords.to_csv(f"{OUTPUT_DIR}/top_keywords.csv", index=False)
print(f"✅ Saved top_keywords.csv ({len(df_keywords)} keywords)")

# ============================================================================
# STEP 3: TOP CHANNELS BY FREQUENCY
# ============================================================================
print("\n📺 STEP 3: Analyzing channel frequencies...")

channel_stats = df.groupby('channel').agg({
    'video_id': 'count',
    'view_count': 'sum',
    'like_count': 'sum',
    'comment_count': 'sum',
    'engagement_score': 'mean'
}).reset_index()

channel_stats.columns = ['channel', 'video_count', 'total_views', 'total_likes', 
                         'total_comments', 'avg_engagement_score']

channel_stats = channel_stats.sort_values('video_count', ascending=False)

# Save channel frequencies
channel_stats.to_csv(f"{OUTPUT_DIR}/freq_by_channel.csv", index=False)
print(f"✅ Saved freq_by_channel.csv ({len(channel_stats)} channels)")

# ============================================================================
# STEP 4: LANGUAGE DETECTION (from text patterns)
# ============================================================================
print("\n🌐 STEP 4: Detecting languages from text patterns...")

def detect_language_hint(text):
    """Simple language detection based on character patterns"""
    if pd.isna(text):
        return 'unknown'
    text = str(text)
    
    # Arabic detection (Unicode range)
    if re.search(r'[\u0600-\u06FF]', text):
        return 'arabic'
    # Check for common language patterns
    elif re.search(r'\b(gaza|palestine|israel|war|news)\b', text.lower()):
        if re.search(r'[а-яА-Я]', text):
            return 'russian'
        elif re.search(r'[à-ÿÀ-Ÿ]', text):
            return 'french'
        elif re.search(r'[ñáéíóúÑÁÉÍÓÚ]', text):
            return 'spanish'
        else:
            return 'english'
    else:
        return 'english'  # default

df['language_hint'] = df.apply(lambda x: detect_language_hint(
    str(x['title']) + ' ' + str(x['description'])
), axis=1)

# Language frequency
lang_freq = df.groupby('language_hint').agg({
    'video_id': 'count',
    'view_count': 'sum'
}).reset_index()
lang_freq.columns = ['language', 'video_count', 'total_views']
lang_freq = lang_freq.sort_values('video_count', ascending=False)

lang_freq.to_csv(f"{OUTPUT_DIR}/freq_by_language.csv", index=False)
print(f"✅ Saved freq_by_language.csv ({len(lang_freq)} languages detected)")
print("   Note: Language detection based on text character patterns")
print("   (YouTube Data API v3 does not provide explicit language field)")

# ============================================================================
# STEP 5: TOP VIDEOS BY ENGAGEMENT
# ============================================================================
print("\n🏆 STEP 5: Ranking top videos by engagement...")

df_top_engagement = df[['video_id', 'title', 'channel', 'view_count', 
                         'like_count', 'comment_count', 'engagement_score', 
                         'engagement_rate']].copy()

df_top_engagement = df_top_engagement.sort_values('engagement_score', ascending=False).head(50)

df_top_engagement.to_csv(f"{OUTPUT_DIR}/top_videos_by_engagement.csv", index=False)
print(f"✅ Saved top_videos_by_engagement.csv (top 50)")

# ============================================================================
# STEP 6: TEMPORAL ANALYSIS (daily aggregation)
# ============================================================================
print("\n📅 STEP 6: Computing temporal trends...")

df_daily = df.groupby('published_date').agg({
    'video_id': 'count',
    'view_count': 'sum',
    'like_count': 'sum',
    'comment_count': 'sum',
    'engagement_score': 'mean'
}).reset_index()

df_daily.columns = ['date', 'videos_published', 'total_views', 'total_likes', 
                    'total_comments', 'avg_engagement_score']

df_daily = df_daily.sort_values('date')

df_daily.to_csv(f"{OUTPUT_DIR}/timeseries_daily.csv", index=False)
print(f"✅ Saved timeseries_daily.csv ({len(df_daily)} days)")

# ============================================================================
# STEP 7: VISUALIZATIONS
# ============================================================================
print("\n📊 STEP 7: Generating visualizations...")

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# 7.1: Top 20 Keywords Bar Plot
print("  📊 Generating barplot_top_keywords.png...")
plt.figure(figsize=(12, 8))
top_20_kw = df_keywords.head(20)
plt.barh(top_20_kw['keyword'][::-1], top_20_kw['frequency'][::-1], color='steelblue')
plt.xlabel('Frequency', fontsize=12)
plt.ylabel('Keyword', fontsize=12)
plt.title('Top 20 Keywords in Gaza YouTube Videos', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/barplot_top_keywords.png", dpi=300, bbox_inches='tight')
plt.close()
print("  ✅ Saved barplot_top_keywords.png")

# 7.2: Top 15 Channels Bar Plot
print("  📊 Generating barplot_top_channels.png...")
plt.figure(figsize=(12, 8))
top_15_ch = channel_stats.head(15)
plt.barh(top_15_ch['channel'][::-1], top_15_ch['video_count'][::-1], color='coral')
plt.xlabel('Number of Videos', fontsize=12)
plt.ylabel('Channel', fontsize=12)
plt.title('Top 15 Channels by Video Count', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/barplot_top_channels.png", dpi=300, bbox_inches='tight')
plt.close()
print("  ✅ Saved barplot_top_channels.png")

# 7.3: Language Distribution Pie Chart
print("  📊 Generating piechart_language.png...")
plt.figure(figsize=(10, 8))
colors = sns.color_palette('pastel')[0:len(lang_freq)]
plt.pie(lang_freq['video_count'], labels=lang_freq['language'], autopct='%1.1f%%',
        startangle=90, colors=colors)
plt.title('Language Distribution (Text Pattern Detection)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/piechart_language.png", dpi=300, bbox_inches='tight')
plt.close()
print("  ✅ Saved piechart_language.png")

# 7.4: Temporal Trends (Time Series)
print("  📊 Generating timeseries_engagement.png...")
fig, axes = plt.subplots(2, 1, figsize=(14, 10))

# Daily videos published
axes[0].plot(df_daily['date'], df_daily['videos_published'], marker='o', 
             linewidth=2, color='darkblue', label='Videos Published')
axes[0].set_xlabel('Date', fontsize=12)
axes[0].set_ylabel('Videos Published', fontsize=12)
axes[0].set_title('Daily Video Publication Trend', fontsize=14, fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].legend()

# Daily engagement
axes[1].plot(df_daily['date'], df_daily['avg_engagement_score'], marker='s', 
             linewidth=2, color='darkgreen', label='Avg Engagement Score')
axes[1].set_xlabel('Date', fontsize=12)
axes[1].set_ylabel('Avg Engagement Score', fontsize=12)
axes[1].set_title('Daily Average Engagement Trend', fontsize=14, fontweight='bold')
axes[1].grid(True, alpha=0.3)
axes[1].legend()

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/timeseries_engagement.png", dpi=300, bbox_inches='tight')
plt.close()
print("  ✅ Saved timeseries_engagement.png")

# 7.5: Word Cloud
print("  📊 Generating wordcloud_keywords.png...")
wordcloud_text = ' '.join([kw for kw, _ in top_keywords[:100]])
wordcloud = WordCloud(width=1600, height=800, background_color='white', 
                      colormap='viridis', max_words=100).generate(wordcloud_text)

plt.figure(figsize=(16, 8))
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis('off')
plt.title('Top 100 Keywords - Word Cloud', fontsize=16, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/wordcloud_keywords.png", dpi=300, bbox_inches='tight')
plt.close()
print("  ✅ Saved wordcloud_keywords.png")

# ============================================================================
# STEP 8: SUMMARY REPORT
# ============================================================================
print("\n📝 STEP 8: Generating summary report...")

summary_report = f"""
# Gaza YouTube Analytics - Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Dataset Overview
- **Total Videos**: {len(df):,}
- **Total Views**: {df['view_count'].sum():,}
- **Total Likes**: {df['like_count'].sum():,}
- **Total Comments**: {df['comment_count'].sum():,}
- **Date Range**: {df['published_date'].min()} to {df['published_date'].max()}
- **Unique Channels**: {df['channel'].nunique()}

## Top 10 Keywords
{df_keywords.head(10).to_string(index=False)}

## Top 10 Channels by Video Count
{channel_stats.head(10)[['channel', 'video_count', 'total_views']].to_string(index=False)}

## Language Distribution
{lang_freq.to_string(index=False)}

Note: Language detection based on text character patterns (Arabic Unicode, Latin scripts).
YouTube Data API v3 does not provide explicit language or country fields for this dataset.

## Top 5 Videos by Engagement Score
{df_top_engagement.head(5)[['title', 'channel', 'view_count', 'engagement_score']].to_string(index=False)}

## Data Fields Available
- video_id, title, description, channel, published_at
- view_count, like_count, comment_count, duration

## Data Fields NOT Available (YouTube API limitation)
- **tags**: Not included in YouTube Data API v3 response for this collection
- **language**: Not explicitly provided; inferred from text patterns
- **country**: Not available in YouTube Data API v3 for video metadata

## Deliverables Generated
✅ top_keywords.csv (50 keywords)
✅ freq_by_channel.csv ({len(channel_stats)} channels)
✅ freq_by_language.csv ({len(lang_freq)} languages - pattern-based detection)
✅ top_videos_by_engagement.csv (top 50 videos)
✅ timeseries_daily.csv ({len(df_daily)} days)
✅ barplot_top_keywords.png
✅ barplot_top_channels.png
✅ piechart_language.png
✅ timeseries_engagement.png
✅ wordcloud_keywords.png

All artifacts saved to: {OUTPUT_DIR}/
"""

with open(f"{OUTPUT_DIR}/SUMMARY_REPORT.txt", 'w', encoding='utf-8') as f:
    f.write(summary_report)

print(summary_report)

print("\n" + "=" * 80)
print("✅ ANALYTICS PIPELINE COMPLETED SUCCESSFULLY!")
print("=" * 80)
print(f"\n📁 All outputs saved to: {OUTPUT_DIR}/")
print("\nGenerated files:")
print("  CSV:")
print("    - top_keywords.csv")
print("    - freq_by_channel.csv")
print("    - freq_by_language.csv")
print("    - top_videos_by_engagement.csv")
print("    - timeseries_daily.csv")
print("  PNG:")
print("    - barplot_top_keywords.png")
print("    - barplot_top_channels.png")
print("    - piechart_language.png")
print("    - timeseries_engagement.png")
print("    - wordcloud_keywords.png")
print("  TXT:")
print("    - SUMMARY_REPORT.txt")
