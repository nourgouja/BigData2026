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

def analyze_sentiment(text, themes=[]):
    """Analyse le sentiment d'un texte (-1 à 1) avec contexte thématique"""
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # Boost de sentiment basé sur les thèmes positifs
        positive_themes = ["admiration", "pride", "inspiration", "solidarity", 
                          "leadership", "resistance", "eloquence", "hope", "martyrdom"]
        negative_themes = ["grief"]
        
        theme_boost = 0.0
        if any(theme in positive_themes for theme in themes):
            theme_boost = 0.15  # Boost positif pour les thèmes positifs
        elif any(theme in negative_themes for theme in themes):
            theme_boost = -0.15
        
        adjusted_polarity = polarity + theme_boost
        
        # Classification avec seuils plus sensibles
        if adjusted_polarity > 0.05:  # Abaissé de 0.1 à 0.05
            return "positive", adjusted_polarity
        elif adjusted_polarity < -0.05:  # Abaissé de -0.1 à -0.05
            return "negative", adjusted_polarity
        else:
            return "neutral", adjusted_polarity
    except:
        return "neutral", 0.0

def detect_abu_obeida_emotions(text):
    """Détecte les émotions et thèmes liés à Abu Obeida"""
    text_lower = text.lower()
    
    emotions_themes = {
        "admiration": ["respect", "hero", "brave", "courage", "legend", "icon", "احترام", "بطل", "شجاع", "أسطورة", "respeto", "héroe", "valiente"],
        "pride": ["proud", "pride", "honor", "فخر", "شرف", "orgullo", "honneur", "fierté"],
        "inspiration": ["inspire", "inspiring", "motivation", "motivate", "إلهام", "حافز", "inspirar", "motivación"],
        "grief": ["rip", "rest in peace", "miss", "sad", "رحمه الله", "افتقد", "descanse", "triste", "repose"],
        "solidarity": ["support", "stand with", "solidarity", "together", "دعم", "تضامن", "معا", "apoyo", "solidaridad"],
        "leadership": ["leader", "leadership", "commander", "قائد", "قيادة", "líder", "liderazgo"],
        "resistance": ["resistance", "fighter", "struggle", "مقاومة", "مجاهد", "resistencia", "lucha"],
        "martyrdom": ["martyr", "shahid", "sacrifice", "شهيد", "تضحية", "mártir", "sacrificio"],
        "eloquence": ["speech", "speaker", "eloquent", "voice", "خطاب", "بليغ", "صوت", "discurso", "elocuente"],
        "hope": ["hope", "freedom", "victory", "أمل", "حرية", "نصر", "esperanza", "libertad", "victoria"]
    }
    
    detected = []
    for theme, keywords in emotions_themes.items():
        if any(keyword in text_lower for keyword in keywords):
            detected.append(theme)
    
    return detected if detected else ["neutral"]

def detect_language_region(text):
    """Détecte la langue/région probable du commentaire"""
    text_sample = text.lower()[:100]
    
    # Vérifier les caractères arabes
    if any('\u0600' <= c <= '\u06FF' for c in text):
        return "Arabic"
    # Mots français courants
    elif any(word in text_sample for word in ['le', 'la', 'les', 'de', 'et', 'que', 'est']):
        return "French"
    # Mots espagnols
    elif any(word in text_sample for word in ['el', 'la', 'los', 'las', 'de', 'que', 'es', 'por']):
        return "Spanish"
    # Mots turcs
    elif any(word in text_sample for word in ['bir', 'bu', 'ile', 've', 'için']):
        return "Turkish"
    # Indonésien/Malais
    elif any(word in text_sample for word in ['yang', 'dan', 'ini', 'untuk']):
        return "Indonesian/Malay"
    else:
        return "English"

# Charger les vidéos Abu Obeida
print("📂 Chargement des vidéos Abu Obeida...")
try:
    with open("abu_obeida_videos.json", "r", encoding='utf-8') as f:
        videos = json.load(f)
except FileNotFoundError:
    print("❌ Fichier abu_obeida_videos.json non trouvé. Exécutez d'abord collect-gaza-videos.py")
    exit()

print(f"✅ {len(videos)} vidéos chargées")

# Analyser les commentaires des vidéos les plus populaires
results = []
videos_to_analyze = sorted(videos, key=lambda x: int(x.get("view_count", 0)), reverse=True)[:30]

print(f"\n🔍 Analyse de sentiments sur {len(videos_to_analyze)} vidéos populaires...\n")

for idx, video in enumerate(videos_to_analyze, 1):
    video_id = video["video_id"]
    title = video["title"][:70]
    
    # Corriger l'affichage de l'arabe dans le terminal
    print(f"{idx}. {fix_arabic_display(title)}...")
    comments = collect_comments(video_id, max_comments=100)
    
    if not comments:
        continue
    
    for comment in comments:
        themes = detect_abu_obeida_emotions(comment["text"])
        sentiment, polarity = analyze_sentiment(comment["text"], themes)
        language = detect_language_region(comment["text"])
        
        results.append({
            "video_id": video_id,
            "video_title": video["title"],
            "channel": video["channel"],
            "comment_text": comment["text"][:300],
            "comment_author": comment["author"],
            "comment_likes": comment["likes"],
            "sentiment": sentiment,
            "polarity": polarity,
            "themes": ", ".join(themes),
            "language_region": language
        })
    
    time.sleep(2)  # Rate limiting

# Sauvegarder les résultats
df = pd.DataFrame(results)
df.to_csv("abu_obeida_sentiments.csv", index=False, encoding='utf-8-sig')

print(f"\n✅ {len(results)} commentaires analysés → abu_obeida_sentiments.csv")

# Statistiques globales
if results:
    print("\n" + "="*60)
    print("📊 ANALYSE GLOBALE - ABU OBEIDA")
    print("="*60)
    
    # Sentiments
    sentiment_counts = Counter([r["sentiment"] for r in results])
    print("\n💭 SENTIMENTS DOMINANTS:")
    for sentiment, count in sentiment_counts.most_common():
        pct = (count / len(results)) * 100
        bar = "█" * int(pct / 2)
        print(f"  {sentiment.upper():10} {count:4} ({pct:5.1f}%) {bar}")
    
    # Thèmes/Émotions
    all_themes = []
    for r in results:
        all_themes.extend(r["themes"].split(", "))
    theme_counts = Counter(all_themes)
    
    print("\n🎯 THÈMES ET ÉMOTIONS DOMINANTS:")
    for theme, count in theme_counts.most_common(15):
        pct = (count / len(results)) * 100
        bar = "█" * int(pct / 3)
        print(f"  {theme:15} {count:4} ({pct:5.1f}%) {bar}")
    
    # Distribution par langue/région
    language_counts = Counter([r["language_region"] for r in results])
    print("\n🌍 DISTRIBUTION PAR LANGUE/RÉGION:")
    for lang, count in language_counts.most_common():
        pct = (count / len(results)) * 100
        bar = "█" * int(pct / 2)
        print(f"  {lang:20} {count:4} ({pct:5.1f}%) {bar}")
    
    # Top commentaires les plus likés (best things said) - avec déduplication
    print("\n⭐ TOP 10 COMMENTAIRES LES PLUS APPRÉCIÉS:")
    # Déduplication par texte de commentaire
    seen_texts = set()
    unique_comments = []
    for r in sorted(results, key=lambda x: x["comment_likes"], reverse=True):
        if r["comment_text"] not in seen_texts:
            seen_texts.add(r["comment_text"])
            unique_comments.append(r)
        if len(unique_comments) >= 10:
            break
    top_comments = unique_comments
    for i, comment in enumerate(top_comments, 1):
        text_preview = fix_arabic_display(comment["comment_text"][:100])
        print(f"\n{i}. 👍 {comment['comment_likes']} likes | {comment['language_region']} | {comment['sentiment'].upper()}")
        print(f"   \"{text_preview}...\"")
        print(f"   Thèmes: {comment['themes']}")
    
    # Sauvegarder les stats
    stats = {
        "total_comments": len(results),
        "total_videos_analyzed": len(videos_to_analyze),
        "sentiments": dict(sentiment_counts),
        "themes": dict(theme_counts.most_common(20)),
        "languages": dict(language_counts),
        "average_polarity": sum(r["polarity"] for r in results) / len(results),
        "top_comments": [
            {
                "text": c["comment_text"],
                "likes": c["comment_likes"],
                "language": c["language_region"],
                "sentiment": c["sentiment"],
                "themes": c["themes"]
            } for c in top_comments
        ]
    }
    
    with open("abu_obeida_stats.json", "w", encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Statistiques détaillées → abu_obeida_stats.json")
    print("="*60)
