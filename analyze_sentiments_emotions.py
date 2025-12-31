import googleapiclient.discovery
import json
import time
from textblob import TextBlob
from collections import Counter
import pandas as pd
import arabic_reshaper
from bidi.algorithm import get_display

# Fonction pour afficher correctement l'arabe dans le terminal
def fix_arabic_display(text):
    """Corrige l'affichage du texte arabe (RTL et jonction des lettres)"""
    if not isinstance(text, str):
        return text
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except:
        return text

API_KEY = "AIzaSyCtPeuVHiK-nlJh04QABzD26FJWhcRZfgU"  
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

def collect_comments(video_id, max_comments=100):
    """Collecte les commentaires d'une vidéo"""
    comments = []
    next_page_token = None
    
    try:
        while len(comments) < max_comments:
            response = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_page_token,
                textFormat="plainText"
            ).execute()
            
            for item in response["items"]:
                comment = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "text": comment["textDisplay"],
                    "author": comment["authorDisplayName"],
                    "likes": comment["likeCount"],
                    "published_at": comment["publishedAt"]
                })
            
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
            time.sleep(0.5)
    except Exception as e:
        print(f"  ⚠️ Commentaires désactivés ou erreur: {str(e)[:50]}")
    
    return comments

def analyze_sentiment(text):
    """Analyse le sentiment d'un texte (-1 à 1)"""
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # Classification
        if polarity > 0.1:
            return "positive", polarity
        elif polarity < -0.1:
            return "negative", polarity
        else:
            return "neutral", polarity
    except:
        return "neutral", 0.0

def detect_emotions(text):
    """Détecte les émotions dominantes basées sur des mots-clés"""
    text_lower = text.lower()
    
    emotions = {
        "colère": ["angry", "furious", "outrage", "disgusted", "hate", "غاضب", "غضب", "enfadado", "odio"],
        "tristesse": ["sad", "tragic", "heartbreaking", "crying", "tears", "حزين", "بكاء", "triste", "lágrimas"],
        "peur": ["scared", "fear", "terrified", "horror", "خوف", "رعب", "miedo", "terror"],
        "espoir": ["hope", "peace", "pray", "better", "أمل", "سلام", "esperanza", "paz"],
        "solidarité": ["support", "solidarity", "together", "help", "تضامن", "دعم", "solidaridad", "apoyo"],
        "indignation": ["injustice", "shame", "wrong", "genocide", "war crime", "ظلم", "جريمة", "injusticia"]
    }
    
    detected = []
    for emotion, keywords in emotions.items():
        if any(keyword in text_lower for keyword in keywords):
            detected.append(emotion)
    
    return detected if detected else ["neutre"]

# Charger les vidéos existantes
print("📂 Chargement des vidéos...")
with open("gaza_videos.json", "r") as f:
    videos = json.load(f)

print(f"✅ {len(videos)} vidéos chargées")

# Analyser les commentaires des vidéos les plus populaires
results = []
videos_to_analyze = sorted(videos, key=lambda x: int(x.get("view_count", 0)), reverse=True)[:20]

print(f"\n🔍 Analyse de sentiments sur {len(videos_to_analyze)} vidéos populaires...\n")

for idx, video in enumerate(videos_to_analyze, 1):
    video_id = video["video_id"]
    title = video["title"][:60]
    
    # Corriger l'affichage de l'arabe dans le terminal
    print(f"{idx}. {fix_arabic_display(title)}...")
    comments = collect_comments(video_id, max_comments=50)
    
    if not comments:
        continue
    
    for comment in comments:
        sentiment, polarity = analyze_sentiment(comment["text"])
        emotions = detect_emotions(comment["text"])
        
        results.append({
            "video_id": video_id,
            "video_title": video["title"],
            "channel": video["channel"],
            "comment_text": comment["text"][:200],
            "comment_likes": comment["likes"],
            "sentiment": sentiment,
            "polarity": polarity,
            "emotions": ", ".join(emotions)
        })
    
    time.sleep(2)  # Rate limiting

# Sauvegarder les résultats
df = pd.DataFrame(results)
df.to_csv("gaza_comments_sentiments.csv", index=False, encoding='utf-8-sig')

print(f"\n✅ {len(results)} commentaires analysés → gaza_comments_sentiments.csv")

# Statistiques globales
if results:
    sentiment_counts = Counter([r["sentiment"] for r in results])
    all_emotions = []
    for r in results:
        all_emotions.extend(r["emotions"].split(", "))
    emotion_counts = Counter(all_emotions)
    
    print("\n📊 SENTIMENTS DOMINANTS:")
    for sentiment, count in sentiment_counts.most_common():
        pct = (count / len(results)) * 100
        print(f"  {sentiment.upper()}: {count} ({pct:.1f}%)")
    
    print("\n😢 ÉMOTIONS DOMINANTES:")
    for emotion, count in emotion_counts.most_common(10):
        pct = (count / len(results)) * 100
        print(f"  {emotion}: {count} ({pct:.1f}%)")
    
    # Sauvegarder les stats
    stats = {
        "total_comments": len(results),
        "sentiments": dict(sentiment_counts),
        "emotions": dict(emotion_counts.most_common(10)),
        "average_polarity": sum(r["polarity"] for r in results) / len(results)
    }
    
    with open("sentiments_stats.json", "w", encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Statistiques sauvegardées → sentiments_stats.json")
