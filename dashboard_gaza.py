import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("whitegrid")
plt.rcParams['figure.facecolor'] = 'white'

# Load data
channels = pd.read_csv('top_channels.csv', names=['channel', 'videos', 'total_views', 'engagement_%'])
# Convert numeric columns from string to numeric
channels['videos'] = pd.to_numeric(channels['videos'], errors='coerce')
channels['total_views'] = pd.to_numeric(channels['total_views'], errors='coerce')
channels['engagement_%'] = pd.to_numeric(channels['engagement_%'], errors='coerce')

full = pd.read_csv('gaza_full_results.csv')

print(f"📊 Loaded: {len(channels)} channels, {len(full)} videos")

# 1. TOP CHANNELS BAR CHART
fig, ax = plt.subplots(figsize=(14, 7))
top10 = channels.head(10).sort_values('total_views')
bars = ax.barh(top10['channel'], top10['total_views']/1e6, color='#2E86AB')
ax.set_xlabel('Total Views (Millions)', fontsize=12, fontweight='bold')
ax.set_title('Top 10 Chaînes YouTube - Gaza War Analysis', fontsize=16, fontweight='bold', pad=20)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
for i, (idx, row) in enumerate(top10.iterrows()):
    ax.text(row['total_views']/1e6 + 1, i, f"{row['videos']} videos", va='center')
plt.tight_layout()
plt.savefig('dashboard_top_channels.png', dpi=300, bbox_inches='tight')
print('✅ Saved: dashboard_top_channels.png')

# 2. ENGAGEMENT SCATTER
fig, ax = plt.subplots(figsize=(12, 7))
scatter_data = full[full['views'] > 0].head(150)
scatter = ax.scatter(scatter_data['views'], scatter_data['likes'], 
                     alpha=0.6, s=80, c=scatter_data['comments'], 
                     cmap='YlOrRd', edgecolors='black', linewidth=0.5)
ax.set_xlabel('Views', fontsize=12, fontweight='bold')
ax.set_ylabel('Likes', fontsize=12, fontweight='bold')
ax.set_title('Engagement Analysis: Views vs Likes (Top 150 Videos)', fontsize=16, fontweight='bold', pad=20)
ax.set_xscale('log')
ax.set_yscale('log')
cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Comments', fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('dashboard_engagement.png', dpi=300, bbox_inches='tight')
print('✅ Saved: dashboard_engagement.png')

# 3. DISTRIBUTION HISTOGRAM
fig, ax = plt.subplots(figsize=(12, 6))
viral_threshold = 1e6
views_data = full[full['views'] > 0]['views']
ax.hist(views_data, bins=50, color='#A23B72', alpha=0.7, edgecolor='black')
ax.axvline(viral_threshold, color='red', linestyle='--', linewidth=2, label=f'Viral Threshold (1M)')
ax.set_xlabel('Views', fontsize=12, fontweight='bold')
ax.set_ylabel('Number of Videos', fontsize=12, fontweight='bold')
ax.set_title('Distribution of Video Views', fontsize=16, fontweight='bold', pad=20)
ax.set_xscale('log')
ax.legend(fontsize=10)
plt.tight_layout()
plt.savefig('dashboard_distribution.png', dpi=300, bbox_inches='tight')
print('✅ Saved: dashboard_distribution.png')

# 4. STATS SUMMARY
print('\n📈 KEY INSIGHTS:')
print(f"  • Total videos analyzed: {len(full)}")
print(f"  • Viral videos (>1M views): {len(full[full['views'] > 1e6])}")
print(f"  • Average views: {full['views'].mean():,.0f}")
print(f"  • Median views: {full['views'].median():,.0f}")
print(f"  • Top channel: {channels.iloc[0]['channel']} ({channels.iloc[0]['videos']} videos)")

print('\n✅✅✅ DASHBOARD COMPLETE - 3 CHARTS READY FOR RAPPORT ✅✅✅')
