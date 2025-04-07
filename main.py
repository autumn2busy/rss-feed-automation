import json
import re
import requests
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from urllib import request

# Define models
@dataclass
class RSSItem:
    title: str
    link: str
    published_date: str
    description: str
    image_url: Optional[str] = None
    category: Optional[str] = ""

# Extract image from HTML description
def _extract_image_url(item: Dict[str, Any]) -> Optional[str]:
    if 'description' in item:
        img_match = re.search(r'<img.+?src=[\'"](.+?)[\'"]', item['description'])
        if img_match:
            return img_match.group(1)
    return None

def _extract_tag_content(xml_str: str, tag: str) -> Optional[str]:
    pattern = f"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, xml_str, re.DOTALL)
    return match.group(1).strip() if match else None

# ✅ Fetch RSS feed using requests
def _fetch_rss_feed(url: str) -> Dict[str, Any]:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/rss+xml,application/xml;q=0.9,*/*;q=0.8'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        content = response.content.decode('utf-8', errors='replace')
        entries: List[Dict[str, str]] = []

        items = content.split('<item>')
        for item in items[1:]:
            item_end_pos = item.find('</item>')
            if item_end_pos > 0:
                item = item[:item_end_pos]

            title = _extract_tag_content(item, 'title') or 'No Title'
            link = _extract_tag_content(item, 'link') or ''
            description = _extract_tag_content(item, 'description') or ''
            published = _extract_tag_content(item, 'pubDate') or ''
            category = _extract_tag_content(item, 'category') or ''

            entry = {
                'title': title,
                'link': link,
                'description': description,
                'published': published,
                'category': category
            }
            entries.append(entry)

        return {"entries": entries}

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while fetching feed {url}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error processing feed {url}: {e}")

    return {"entries": []}

# Get new items
def _get_new_items(feeds: List[str], seen_items: Set[str]) -> List[RSSItem]:
    new_items = []

    for feed_url in feeds:
        print(f"📥 Fetching feed: {feed_url}")
        feed = _fetch_rss_feed(feed_url)

        for entry in feed["entries"][:10]:
            item_id = entry.get('link', '')
            if item_id not in seen_items:
                image_url = _extract_image_url(entry)
                item = RSSItem(
                    title=entry.get('title', 'No Title'),
                    link=entry.get('link', ''),
                    published_date=entry.get('published', ''),
                    description=entry.get('description', ''),
                    image_url=image_url,
                    category=entry.get('category', '')
                )
                new_items.append(item)
                seen_items.add(item_id)

    return new_items

# Prepare Wix payload
def _prepare_wix_payload(item: RSSItem) -> dict:
    return {
        "title": item.title,
        "summary": item.description,
        "image": item.image_url or "",
        "link": item.link,
        "category": item.category,
        "publishedDate": item.published_date,
        "featured": False
    }

# ✅ Insert to Wix using proper API format
def _send_to_wix_api(items: list) -> dict:
    api_url = "https://www.wixapis.com/data/v2/collections/news_feed/items"  # 👈 Replace with your actual collection ID
    headers = {
        "Authorization": "Bearer YOUR_REAL_WIX_API_KEY",  # 👈 Replace with your actual token
        "Content-Type": "application/json"
    }

    results = []

    for item in items:
        payload = _prepare_wix_payload(item)
        full_payload = json.dumps({ "data": payload }).encode('utf-8')
        print("📦 Payload to Wix:", json.dumps(payload, indent=2))

        req = request.Request(api_url, data=full_payload, headers=headers, method='POST')

        try:
            opener = request.build_opener()
            with opener.open(req) as response:
                response_data = json.loads(response.read().decode())
                results.append(response_data)
                print(f"✅ Successfully inserted: {payload['title']}")
        except Exception as e:
            print(f"❌ Failed to insert item to Wix: {e}")

    return {"sent_count": len(results), "results": results}

# Fetch and process
def fetch_and_process_feeds(feeds: List[str]) -> List[RSSItem]:
    seen_items: Set[str] = set()
    return _get_new_items(feeds, seen_items)

# Main automation function
def run_daily_rss_to_wix() -> Dict[str, Any]:
    feeds = [
        "https://www.usda.gov/about-usda/policies-and-links/digital/rss-feeds",
        "https://www.hud.gov/sites/dfiles/Main/documents/hudrss.xml",
        "https://www.huduser.gov/rss/pub.xml",
        "https://www.usda.gov/rss-feeds",
        "https://appraisersblogs.com/feed",
        "https://www.nationalmortgagenews.com/feed?rss=true",
        "https://www.consumerfinance.gov/about-us/blog/feed/",
        "https://freddiemac.gcs-web.com/rss/news-releases.xml"
    ]

    processed_items = fetch_and_process_feeds(feeds)
    print(f"📊 Found {len(processed_items)} new items")

    if processed_items:
        result = _send_to_wix_api(processed_items)
        print(f"🚀 Sent {result.get('sent_count', 0)} items to Wix")
        return result
    else:
        print("🟡 No new items to send to Wix")
        return {"sent_count": 0, "results": []}

# CLI Entry point
def run_feed_automation() -> None:
    print("🛠 Starting RSS feed automation...")
    result = run_daily_rss_to_wix()
    print(f"✅ Completed automation. Processed {result.get('sent_count', 0)} items.")

# Trigger when run
if __name__ == "__main__":
    run_feed_automation()
