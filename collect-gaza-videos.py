import googleapiclient.discovery
import json
import time
import argparse
from datetime import datetime, timedelta

API_KEY = "AIzaSyCtPeuVHiK-nlJh04QABzD26FJWhcRZfgU"  
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

def collect_videos(query, max_results=200, published_after="2023-10-07T00:00:00Z"):
    """
    Collect YouTube videos matching the query.
    
    Args:
        query: Search query string
        max_results: Maximum number of videos to collect
        published_after: ISO 8601 date (default: Oct 7, 2023 - Gaza war start)
    
    Returns:
        List of video dictionaries with metadata
    """
    videos = []
    next_page_token = None
    
    while len(videos) < max_results:
        try:
            search_response = youtube.search().list(
                q=query,
                part="snippet",
                maxResults=min(50, max_results - len(videos)),
                pageToken=next_page_token,
                type="video",
                order="viewCount",
                publishedAfter=published_after
            ).execute()
            
            for item in search_response["items"]:
                video_id = item["id"]["videoId"]
                
                # Get detailed video information
                video_details = youtube.videos().list(
                    part="snippet,statistics,contentDetails",
                    id=video_id
                ).execute()["items"][0]
                
                videos.append({
                    "video_id": video_id,
                    "title": video_details["snippet"]["title"],
                    "description": video_details["snippet"]["description"],
                    "channel": video_details["snippet"]["channelTitle"],
                    "published_at": video_details["snippet"]["publishedAt"],
                    "view_count": video_details["statistics"].get("viewCount", 0),
                    "like_count": video_details["statistics"].get("likeCount", 0),
                    "comment_count": video_details["statistics"].get("commentCount", 0),
                    "duration": video_details["contentDetails"]["duration"]
                })
            
            next_page_token = search_response.get("nextPageToken")
            if not next_page_token:
                break
            
            time.sleep(1)  # Rate limiting
        
        except Exception as e:
            print(f"⚠️  Error collecting '{query}': {e}")
            break
    
    return videos[:max_results]

# ============================================
# GAZA WAR ANALYSIS - Multi-language Queries
# Focus: Israel-Gaza conflict since Oct 7, 2023
# ============================================
def main(args):
    """Main collection function"""
    queries = [
        # English - General conflict coverage
        "Gaza war", 
        "Palestine Israel conflict", 
        "Gaza Palestine", 
        "Israel Hamas war",
        "Gaza crisis 2023",
        
        # Arabic - Regional news coverage  
        "غزة",                    # Gaza
        "فلسطين إسرائيل",         # Palestine Israel
        "حرب غزة",                # Gaza war
        "القدس فلسطين",           # Jerusalem Palestine
        "غزة الآن",               # Gaza now
        
        # Spanish - Latin American coverage
        "guerra de Gaza", 
        "Palestina Israel", 
        "conflicto Gaza",
        
        # French - European/African coverage
        "guerre Gaza",
        "conflit Palestine",
        "Gaza actualité",
        
        # Turkish - Regional Middle East
        "Gazze savaşı",
        "Filistin İsrail"
    ]

    all_videos = []
    seen_video_ids = set()  # Deduplication
    
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Collecting '{query}'...")
        videos = collect_videos(query, max_results=args.max_results, published_after=args.date_from)
        
        # Deduplicate videos
        unique_videos = [v for v in videos if v["video_id"] not in seen_video_ids]
        seen_video_ids.update(v["video_id"] for v in unique_videos)
        
        all_videos.extend(unique_videos)
        print(f"    ✅ Found {len(videos)} videos ({len(unique_videos)} unique)")
        time.sleep(2)  # Respect API rate limits

    # Save to JSON
    output_json = f"{args.output}.json"
    output_jsonl = f"{args.output}.jsonl"
    
    with open(output_json, "w", encoding='utf-8') as f:
        json.dump(all_videos, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Collected {len(all_videos)} unique videos → {output_json}")
    print(f"📊 Queries used: {len(queries)} multi-language search terms")
    print(f"📅 Date range: Since {args.date_from[:10]}")

    # Convert to JSONL format for HDFS
    print(f"\n📝 Converting to JSONL format...")
    with open(output_jsonl, "w", encoding='utf-8') as f:
        for video in all_videos:
            f.write(json.dumps(video, ensure_ascii=False) + "\n")

    print(f"✅ Saved JSONL format → {output_jsonl} (HDFS-ready)")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect YouTube videos about Gaza conflict using multi-language queries"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Maximum videos per query (default: 50)"
    )
    parser.add_argument(
        "--date-from",
        type=str,
        default="2023-10-07T00:00:00Z",
        help="Start date in ISO 8601 format (default: 2023-10-07 - Gaza war start)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="gaza_videos",
        help="Output filename prefix (default: gaza_videos)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("GAZA WAR VIDEO COLLECTOR - YouTube Data API v3")
    print("=" * 60)
    print(f"📅 Date from: {args.date_from}")
    print(f"📊 Max results per query: {args.max_results}")
    print(f"📝 Output: {args.output}.json / {args.output}.jsonl")
    print("=" * 60)
    
    # Run main collection
    main(args)
