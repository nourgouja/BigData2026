import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import arabic_reshaper
from bidi.algorithm import get_display

# Fonction pour afficher correctement l'arabe
def fix_arabic_text(text):
    """Corrige l'affichage du texte arabe (RTL et jonction des lettres)"""
    if not isinstance(text, str):
        return text
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except:
        return text

# Configuration du style
sns.set_style("whitegrid")
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['font.size'] = 10

# Charger les données
with open('sentiments_stats.json', 'r', encoding='utf-8') as f:
    stats = json.load(f)

comments_df = pd.read_csv('gaza_comments_sentiments.csv', encoding='utf-8-sig')

print(f"📊 Chargé: {len(comments_df)} commentaires analysés")

# Créer une figure avec plusieurs sous-graphiques
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

# 1. PIE CHART - Distribution des sentiments
ax1 = fig.add_subplot(gs[0, 0])
sentiments = stats['sentiments']
colors_sentiment = {'positive': '#4CAF50', 'neutral': '#9E9E9E', 'negative': '#F44336'}
colors = [colors_sentiment.get(s, '#9E9E9E') for s in sentiments.keys()]
wedges, texts, autotexts = ax1.pie(sentiments.values(), labels=sentiments.keys(), 
                                     autopct='%1.1f%%', colors=colors,
                                     startangle=90, textprops={'fontsize': 11, 'weight': 'bold'})
ax1.set_title('Distribution des Sentiments', fontsize=14, fontweight='bold', pad=15)

# 2. BAR CHART - Top émotions
ax2 = fig.add_subplot(gs[0, 1])
emotions = dict(list(stats['emotions'].items())[:8])
emotion_colors = {
    'neutre': '#9E9E9E', 'colère': '#D32F2F', 'tristesse': '#1976D2',
    'peur': '#7B1FA2', 'espoir': '#388E3C', 'solidarité': '#F57C00',
    'indignation': '#C2185B'
}
colors_bar = [emotion_colors.get(e, '#607D8B') for e in emotions.keys()]
bars = ax2.barh(list(emotions.keys()), list(emotions.values()), color=colors_bar)
ax2.set_xlabel('Nombre de mentions', fontsize=11, fontweight='bold')
ax2.set_title('Émotions Dominantes', fontsize=14, fontweight='bold', pad=15)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
for i, (emotion, count) in enumerate(emotions.items()):
    ax2.text(count + 5, i, str(count), va='center', fontsize=10, fontweight='bold')

# 3. POLARITÉ MOYENNE
ax3 = fig.add_subplot(gs[1, 0])
avg_polarity = stats['average_polarity']
ax3.barh(['Polarité Globale'], [avg_polarity], color='#2196F3', height=0.3)
ax3.set_xlim(-1, 1)
ax3.axvline(0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
ax3.set_xlabel('Polarité (-1: Négatif, +1: Positif)', fontsize=11, fontweight='bold')
ax3.set_title(f'Polarité Moyenne: {avg_polarity:.3f}', fontsize=14, fontweight='bold', pad=15)
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)

# 4. DISTRIBUTION DE POLARITÉ (Histogram)
ax4 = fig.add_subplot(gs[1, 1])
polarity_data = comments_df['polarity'].dropna()
n, bins, patches = ax4.hist(polarity_data, bins=30, color='#607D8B', alpha=0.7, edgecolor='black')
# Colorer les barres selon le sentiment
for i, patch in enumerate(patches):
    if bins[i] < -0.1:
        patch.set_facecolor('#F44336')
    elif bins[i] > 0.1:
        patch.set_facecolor('#4CAF50')
    else:
        patch.set_facecolor('#9E9E9E')
ax4.axvline(0, color='black', linestyle='--', linewidth=1.5, label='Neutre')
ax4.set_xlabel('Polarité', fontsize=11, fontweight='bold')
ax4.set_ylabel('Nombre de commentaires', fontsize=11, fontweight='bold')
ax4.set_title('Distribution de la Polarité', fontsize=14, fontweight='bold', pad=15)
ax4.legend()
ax4.grid(True, alpha=0.3)

# 5. TOP VIDÉOS PAR SENTIMENT (Positif vs Négatif)
ax5 = fig.add_subplot(gs[2, :])
video_sentiments = comments_df.groupby(['video_title', 'sentiment']).size().unstack(fill_value=0)
video_sentiments['total'] = video_sentiments.sum(axis=1)
top_videos = video_sentiments.nlargest(10, 'total')

# Tronquer les titres et corriger l'arabe
top_videos.index = [fix_arabic_text(title[:50] + '...' if len(title) > 50 else title) for title in top_videos.index]

x = range(len(top_videos))
width = 0.25

if 'positive' in top_videos.columns:
    ax5.bar([i - width for i in x], top_videos['positive'], width, label='Positif', color='#4CAF50')
if 'neutral' in top_videos.columns:
    ax5.bar(x, top_videos['neutral'], width, label='Neutre', color='#9E9E9E')
if 'negative' in top_videos.columns:
    ax5.bar([i + width for i in x], top_videos['negative'], width, label='Négatif', color='#F44336')

ax5.set_xlabel('Vidéos', fontsize=11, fontweight='bold')
ax5.set_ylabel('Nombre de commentaires', fontsize=11, fontweight='bold')
ax5.set_title('Top 10 Vidéos par Sentiments des Commentaires', fontsize=14, fontweight='bold', pad=15)
ax5.set_xticks(x)
ax5.set_xticklabels(top_videos.index, rotation=45, ha='right', fontsize=9)
ax5.legend()
ax5.spines['top'].set_visible(False)
ax5.spines['right'].set_visible(False)
ax5.grid(True, alpha=0.3, axis='y')

# Titre global
fig.suptitle('📊 Analyse des Sentiments et Émotions - Guerre de Gaza', 
             fontsize=18, fontweight='bold', y=0.98)

# Ajouter des statistiques en texte
textstr = f'''Total: {stats['total_comments']} commentaires
Positif: {stats['sentiments'].get('positive', 0)} ({stats['sentiments'].get('positive', 0)/stats['total_comments']*100:.1f}%)
Neutre: {stats['sentiments'].get('neutral', 0)} ({stats['sentiments'].get('neutral', 0)/stats['total_comments']*100:.1f}%)
Négatif: {stats['sentiments'].get('negative', 0)} ({stats['sentiments'].get('negative', 0)/stats['total_comments']*100:.1f}%)'''

fig.text(0.02, 0.02, textstr, fontsize=9, verticalalignment='bottom',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

plt.savefig('sentiment_analysis_dashboard.png', dpi=300, bbox_inches='tight')
print('\n✅ Dashboard sauvegardé: sentiment_analysis_dashboard.png')

# Créer un second dashboard pour les émotions détaillées
fig2, axes = plt.subplots(2, 2, figsize=(14, 10))
fig2.suptitle('😢 Analyse Détaillée des Émotions', fontsize=16, fontweight='bold')

# 1. Émotions par vidéo (heatmap)
ax_heat = axes[0, 0]
# Créer une table d'émotions par vidéo
emotion_data = []
for _, row in comments_df.iterrows():
    emotions_list = row['emotions'].split(', ')
    for emotion in emotions_list:
        emotion_data.append({'video': fix_arabic_text(row['video_title'][:40]), 'emotion': emotion})

emotion_video_df = pd.DataFrame(emotion_data)
emotion_pivot = emotion_video_df.groupby(['video', 'emotion']).size().unstack(fill_value=0)

if len(emotion_pivot) > 0:
    top_emotion_videos = emotion_pivot.iloc[:8]  # Top 8 vidéos
    # Corriger les labels d'émotions si nécessaire
    top_emotion_videos.columns = [fix_arabic_text(str(col)) for col in top_emotion_videos.columns]
    sns.heatmap(top_emotion_videos, annot=True, fmt='d', cmap='YlOrRd', 
                ax=ax_heat, cbar_kws={'label': 'Mentions'})
    ax_heat.set_title('Émotions par Vidéo', fontweight='bold')
    ax_heat.set_xlabel('')
    ax_heat.set_ylabel('Vidéo', fontweight='bold')

# 2. Timeline des sentiments (si données temporelles disponibles)
ax_time = axes[0, 1]
if 'published_at' in comments_df.columns:
    comments_df['date'] = pd.to_datetime(comments_df['published_at'], errors='coerce')
    daily_sentiment = comments_df.groupby([comments_df['date'].dt.date, 'sentiment']).size().unstack(fill_value=0)
    if len(daily_sentiment) > 0:
        daily_sentiment.plot(ax=ax_time, color={'positive': '#4CAF50', 'neutral': '#9E9E9E', 'negative': '#F44336'})
        ax_time.set_title('Évolution des Sentiments', fontweight='bold')
        ax_time.set_xlabel('Date', fontweight='bold')
        ax_time.set_ylabel('Nombre de commentaires', fontweight='bold')
        ax_time.legend(title='Sentiment')
        ax_time.grid(True, alpha=0.3)
else:
    ax_time.text(0.5, 0.5, 'Données temporelles\nnon disponibles', 
                 ha='center', va='center', fontsize=12)
    ax_time.axis('off')

# 3. Commentaires les plus likés par sentiment
ax_likes = axes[1, 0]
top_liked = comments_df.nlargest(5, 'comment_likes')[['sentiment', 'comment_likes']]
sentiment_likes = top_liked.groupby('sentiment')['comment_likes'].sum()
ax_likes.bar(sentiment_likes.index, sentiment_likes.values, 
            color=[colors_sentiment.get(s, '#9E9E9E') for s in sentiment_likes.index])
ax_likes.set_title('Likes Totaux par Sentiment (Top 5)', fontweight='bold')
ax_likes.set_ylabel('Nombre de likes', fontweight='bold')
ax_likes.spines['top'].set_visible(False)
ax_likes.spines['right'].set_visible(False)

# 4. Statistiques textuelles
ax_text = axes[1, 1]
ax_text.axis('off')
stats_text = f'''
📌 STATISTIQUES CLÉS

Total Commentaires: {stats['total_comments']}

Polarité Moyenne: {stats['average_polarity']:.3f}

TOP 5 ÉMOTIONS:
'''
for i, (emotion, count) in enumerate(list(stats['emotions'].items())[:5], 1):
    pct = (count / stats['total_comments']) * 100
    stats_text += f'{i}. {emotion.capitalize()}: {count} ({pct:.1f}%)\n'

ax_text.text(0.1, 0.9, stats_text, fontsize=11, verticalalignment='top',
            fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

plt.tight_layout()
plt.savefig('emotions_detailed_dashboard.png', dpi=300, bbox_inches='tight')
print('✅ Dashboard émotions sauvegardé: emotions_detailed_dashboard.png')

print('\n🎯 Analyse terminée! Vérifiez les fichiers PNG générés.')
