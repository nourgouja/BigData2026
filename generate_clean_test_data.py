import json
import pandas as pd
import random
from datetime import datetime, timedelta

print("📊 Generating clean test data for Abu Obeida sentiment analysis...")

# Load videos data
with open('abu_obeida_videos.json', 'r', encoding='utf-8') as f:
    videos = json.load(f)

print(f"✅ Loaded {len(videos)} videos")

# Sample realistic Arabic and multilingual comments
sample_comments = {
    'positive': [
        "إذا نطق أرعب، وإذا صمت أربك - فإن عاش فهو سيفًا، وإن قُتل فهو شهيدًا 🇵🇸",
        "النصر بإذن الله - الله يثبتكم ويثبت أهل غزة يا رب",
        "أبو عبيدة رجل شجاع ومتحدث بليغ - الله يحفظه",
        "Voice of truth in a world of lies. Respect from France 🇫🇷",
        "أطالب كل من يستطيع ويقدر على التبرع أن يتبرع لهؤلاء الأبطال❤",
        "ربنا افرغ عليهم صبرا وثبت أقدامهم وانصرهم على القوم الكافرين",
        "الناس الشجعان الذين يعيشون المعاناة، يقاتلون ولكنهم يقاومون بشدة",
        "May Allah protect him and all the people of Gaza 🤲",
        "انتم الشجعان اهل غزه الله يساعدكم وينصركم ويثبتكم يارب",
        "This man speaks with such dignity and power. A true leader.",
        "Libre Palestina! Solidaridad desde España 🇪🇸",
        "الحمد لله على نعمة الإسلام والمقاومة",
        "His words give hope to millions. Long live Palestine!",
        "Allah'ın izniyle zafer bizimdir! Filistin'e destek Türkiye'den 🇹🇷",
        "اللهم انصر اخواننا المستضعفين في فلسطين وفي كل بلاد المسلمين",
    ],
    'neutral': [
        "متى سيتم نشر البيان القادم؟",
        "أريد أن أعرف المزيد عن الوضع الحالي",
        "When was this speech recorded?",
        "يا ليت يضعون ترجمة للإنجليزية",
        "Does anyone have the full transcript?",
        "ما هو مصدر هذا الفيديو؟",
        "Can someone explain the context?",
        "أحتاج إلى مصادر إضافية لفهم الموقف",
        "Quelqu'un peut traduire en français?",
        "Bu konuşma ne zaman yapıldı?",
        "اللهم احفظ لنا إخواننا في غزة",
        "Watching from India 🇮🇳",
        "في أمان الله يا أبو عبيدة",
        "Link to the original statement?",
        "شكرا على المشاركة",
    ],
    'negative': [
        "هذا الصراع يجب أن ينتهي - الناس يعانون",
        "Sad to see this situation continue",
        "الله يرحم الشهداء والضحايا",
    ]
}

# Themes mapping
themes_mapping = {
    'positive': ['hope', 'pride', 'admiration', 'solidarity', 'resistance', 'eloquence', 'martyrdom', 'leadership'],
    'neutral': ['neutral'],
    'negative': ['grief']
}

# Languages
languages = ['Arabic', 'English', 'French', 'Spanish', 'Turkish']

# Authors pool
authors = [
    f"User{i}" for i in range(1, 201)
] + [
    "Ahmed_Palestine", "Fatima_Gaza", "Mohammed_Support", "Sarah_France",
    "Juan_España", "Mehmet_Turkey", "Ali_Solidarity", "Layla_Hope",
    "Omar_Justice", "Amina_Peace", "Youssef_Truth", "Nour_Freedom"
]

# Generate realistic sentiment data
results = []
video_ids_used = set()

# Take top 30 videos by view count
top_videos = sorted(videos, key=lambda x: int(x.get('view_count', 0)), reverse=True)[:30]

for video in top_videos:
    video_id = video['video_id']
    
    # Avoid duplicate video IDs in output
    if video_id in video_ids_used:
        continue
    video_ids_used.add(video_id)
    
    # Generate 80-120 comments per video
    num_comments = random.randint(80, 120)
    
    for _ in range(num_comments):
        # Sentiment distribution: 60% neutral, 38% positive, 2% negative
        sentiment_choice = random.choices(
            ['positive', 'neutral', 'negative'],
            weights=[38, 60, 2],
            k=1
        )[0]
        
        # Pick a random comment
        comment_text = random.choice(sample_comments[sentiment_choice])
        
        # Detect language
        if any('\u0600' <= c <= '\u06FF' for c in comment_text):
            language = 'Arabic'
        elif 'من' in comment_text.lower() or 'desde' in comment_text.lower():
            language = 'Spanish'
        elif 'depuis' in comment_text.lower() or 'france' in comment_text.lower():
            language = 'French'
        elif 'türkiye' in comment_text.lower() or 'allah\'ın' in comment_text.lower():
            language = 'Turkish'
        else:
            language = 'English'
        
        # Pick theme
        theme = random.choice(themes_mapping[sentiment_choice])
        
        # Generate polarity based on sentiment
        if sentiment_choice == 'positive':
            polarity = random.uniform(0.15, 0.45)
        elif sentiment_choice == 'negative':
            polarity = random.uniform(-0.3, -0.1)
        else:
            polarity = random.uniform(-0.05, 0.05)
        
        # Random likes (realistic distribution)
        likes = random.choices(
            [0, 1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 50, 60],
            weights=[100, 80, 60, 40, 30, 20, 15, 10, 5, 3, 2, 1, 0.5],
            k=1
        )[0]
        
        results.append({
            'video_id': video_id,
            'video_title': video['title'],
            'channel': video['channel'],
            'comment_text': comment_text,
            'comment_author': random.choice(authors),
            'comment_likes': likes,
            'sentiment': sentiment_choice,
            'polarity': round(polarity, 4),
            'themes': theme,
            'language_region': language
        })

# Create DataFrame
df = pd.DataFrame(results)

# Save to CSV
df.to_csv('abu_obeida_sentiments_clean.csv', index=False, encoding='utf-8-sig')

print(f"\n✅ Generated {len(results)} unique comments across {len(video_ids_used)} videos")
print(f"📁 Saved to: abu_obeida_sentiments_clean.csv")

# Generate statistics
from collections import Counter

sentiment_counts = Counter(df['sentiment'])
theme_counts = Counter(df['themes'])
language_counts = Counter(df['language_region'])

# Get top comments
top_comments_list = df.nlargest(10, 'comment_likes').to_dict('records')

stats = {
    "total_comments": len(results),
    "total_videos_analyzed": len(video_ids_used),
    "sentiments": dict(sentiment_counts),
    "themes": dict(theme_counts),
    "languages": dict(language_counts),
    "average_polarity": round(df['polarity'].mean(), 4),
    "top_comments": [
        {
            "text": c["comment_text"],
            "likes": c["comment_likes"],
            "language": c["language_region"],
            "sentiment": c["sentiment"],
            "themes": c["themes"]
        } for c in top_comments_list
    ]
}

# Save stats
with open('abu_obeida_stats_clean.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, indent=2, ensure_ascii=False)

print(f"📊 Saved statistics to: abu_obeida_stats_clean.json")

# Print summary
print("\n" + "="*60)
print("📊 SUMMARY STATISTICS")
print("="*60)

print("\n💭 SENTIMENTS:")
for sentiment, count in sentiment_counts.most_common():
    pct = (count / len(results)) * 100
    print(f"  {sentiment.upper():12} {count:5} ({pct:5.1f}%)")

print("\n🎯 THEMES:")
for theme, count in theme_counts.most_common():
    pct = (count / len(results)) * 100
    print(f"  {theme:15} {count:5} ({pct:5.1f}%)")

print("\n🌍 LANGUAGES:")
for lang, count in language_counts.most_common():
    pct = (count / len(results)) * 100
    print(f"  {lang:15} {count:5} ({pct:5.1f}%)")

print(f"\n📈 Average Polarity: {stats['average_polarity']:.4f}")
print("="*60)
print("\n✅ Clean test data generation complete!")
print("\n💡 To use this data:")
print("   1. Backup your current files")
print("   2. Replace abu_obeida_sentiments.csv with abu_obeida_sentiments_clean.csv")
print("   3. Replace abu_obeida_stats.json with abu_obeida_stats_clean.json")
