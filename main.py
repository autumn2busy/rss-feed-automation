import json
import datetime
from typing import List, Dict, Any, Optional, Set
from urllib import request
from dataclasses import dataclass

# Define models
@dataclass
class RSSItem:
    """Model for an RSS feed item"""
    title: str
    link: str
    published_date: str
    description: str
    image_url: Optional[str] = None
    category: Optional[str] = ""

# Function to extract image URL from RSS item
def _extract_image_url(item: Dict[str, Any]) -> Optional[str]:
    """Extract image URL from RSS item if available"""
    # Look for image in description (simple regex approach)
    if 'description' in item:
        import re
        img_match = re.search(r'<img.+?src=[\'"](.+?)[\'"]', item['description'])
        if img_match:
            return img_match.group(1)
    
    return None

def _extract_tag_content(xml_str: str, tag: str) -> Optional[str]:
    """Helper function to extract content between XML tags"""
    import re
    pattern: str = f"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, xml_str, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

# Function to fetch RSS feed
def _fetch_rss_feed(url: str) -> Dict[str, Any]:
    """Fetch and parse RSS feed content"""
    try:
        # Create an opener that adds a user agent
        opener: request.OpenerDirector = request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        
        # Fetch the content
        with opener.open(url) as response:
            content: str = response.read().decode('utf-8')
            
        # Simple XML parsing using string operations
        entries: List[Dict[str, str]] = []
        
        # Split content into items
        items: List[str] = content.split('<item>')
        for item in items[1:]:  # Skip the first split as it's the header
            item_end_pos: int = item.find('</item>')
            if item_end_pos > 0:
                item = item[:item_end_pos]  # Trim to just the item content

            # Extract basic fields using string operations
            title: str = _extract_tag_content(item, 'title') or 'No Title'
            link: str = _extract_tag_content(item, 'link') or ''
            description: str = _extract_tag_content(item, 'description') or ''
            published: str = _extract_tag_content(item, 'pubDate') or ''
            category: str = _extract_tag_content(item, 'category') or ''
            
            entry: Dict[str, str] = {
                'title': title,
                'link': link,
                'description': description,
                'published': published,
                'category': category
            }
            entries.append(entry)
        
        return {"entries": entries}
    except Exception as e:
        print(f"Error fetching feed {url}: {str(e)}")
        return {"entries": []}

# Function to get new items from feeds
def _get_new_items(feeds: List[str], seen_items: Set[str]) -> List[RSSItem]:
    """Fetch RSS feeds and return new items not seen before"""
    new_items = []
    
    for feed_url in feeds:
        try:
            print(f"Fetching feed: {feed_url}")
            feed = _fetch_rss_feed(feed_url)
            
            for entry in feed["entries"][:10]:  # Process up to 10 latest entries
                # Create a unique ID for this item
                item_id = f"{entry.get('link', '')}"
                
                if item_id not in seen_items:
                    # Extract image URL
                    image_url = _extract_image_url(entry)
                    
                    # Create RSS item
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
        except Exception as e:
            print(f"Error processing feed {feed_url}: {e}")
    
    return new_items

# Function to prepare Wix payload from RSS item
def _prepare_wix_payload(item: RSSItem) -> dict:
    """
    Transform RSS item into the format expected by Wix collection.
    """
    # Map RSS item fields to Wix collection fields
    return {
        "title": item.title if hasattr(item, 'title') else "",
        "summary": item.description if hasattr(item, 'description') else "",
        "image": item.image_url if hasattr(item, 'image_url') else "",
        "link": item.link if hasattr(item, 'link') else "",
        "category": item.category if hasattr(item, 'category') else "",
        "publishedDate": item.published_date if hasattr(item, 'published_date') else "",
        "featured": False  # Default value for featured items
    }

# Function to send items to Wix API
def _send_to_wix_api(items: list) -> dict:
    """
    Send processed RSS items to Wix collection via the Wix Data API.
    """
    from urllib import request
    import json
    
    # Wix API configuration - using values from your curl command
    api_url: str = "https://www.wixapis.com/data/v2/collections/NewsFeed/items"
    
    # Authentication headers from your curl command
    headers: dict = {
        "Authorization": "IST.eyJraWQiOiJQb3pIX2FDMiIsImFsZyI6IlJTMjU2In0.eyJkYXRhIjoie1wiaWRcIjpcImNjMGNiNWVlLWQ4MzQtNDNkYi05ODA5LTA5ZDZiMTc5MTllMFwiLFwiaWRlbnRpdHlcIjp7XCJ0eXBlXCI6XCJhcHBsaWNhdGlvblwiLFwiaWRcIjpcIjRmNWRhYTA4LWE1YzQtNDgyZC1iZDNmLWY4MzAzMmI5ZDMzM1wifSxcInRlbmFudFwiOntcInR5cGVcIjpcImFjY291bnRcIixcImlkXCI6XCJmOWJhZmU1YS05MjA1LTRlZDEtYjNiOC0yZGI4YTQ3OGY4ODVcIn19IiwiaWF0IjoxNzQzOTc2Njc5fQ.KWizNJ5pHIF3Z4X2iIONQ7x46vIFwBuvQEUTRCL3TGp0f4J-C3wejPEDRBDbVY7POI5iYyHNQZ7sf30nwpzgQLurWwihb4K8Lr9yZUa9vzOewqnc-R2E-wlXx1-fJOg8nnUEMo8m6gGNUpAC6l4_aekuidMROCvjmC5N4R6yG3Ieze71kYwMj6XGnn-20TSKQUw6Y32XCDmk9mtfUYkip2ydN5cty8oe36yFL40atyc9DBFNAln5kCKmzub2TZH474aVqD2NWnNLUlRt7qwaPpflG6W_Y-d0HxCZIZxgtJHjciyZ4lqypo1H4ZVQ6VkCjI1ZUK-G6rl_xEpwRBpPpw",
        "wix-account-id": "f9bafe5a-9205-4ed1-b3b8-2db8a478f885",
        "wix-site-id": "2b8b6470-c179-4c8c-8f0f-ce7865e6d713",
        "Content-Type": "application/json"
    }
    
    # Process each item and send in individual requests
    results: list = []
    
    for item in items:
        # Prepare the individual item payload
        payload: dict = _prepare_wix_payload(item)
        
        # Create request with headers
        payload_bytes: bytes = json.dumps(payload).encode('utf-8')
        req: request.Request = request.Request(
            api_url,
            data=payload_bytes,
            headers=headers,
            method='POST'
        )
        
        # Send request to Wix API
        print(f"Sending item '{payload.get('title', 'Untitled')}' to Wix collection")
        try:
            # Create an opener that adds a user agent
            opener: request.OpenerDirector = request.build_opener()
            with opener.open(req) as response:
                response_data: dict = json.loads(response.read().decode())
                results.append(response_data)
                print(f"Successfully sent item to Wix: {payload.get('title', 'Untitled')}")
        except Exception as e:
            error_msg: str = f"Failed to send item to Wix: {str(e)}"
            print(error_msg)
            # Continue with other items even if one fails
    
    return {"sent_count": len(results), "results": results}

# Function to fetch and process feeds
def fetch_and_process_feeds(feeds: List[str]) -> List[RSSItem]:
    """Fetch and process RSS feeds, returning new items"""
    # Initialize empty set for seen items (won't persist between runs)
    seen_items: Set[str] = set()
    
    # Get new items from feeds
    new_items: List[RSSItem] = _get_new_items(feeds, seen_items)
    
    return new_items

# Function to run RSS to Wix automation
def run_daily_rss_to_wix() -> Dict[str, Any]:
    """Main function to run the RSS to Wix automation"""
    # List of RSS feeds to monitor
    feeds: List[str] = [
https://www.usda.gov/about-usda/policies-and-links/digital/rss-feeds,
https://www.hud.gov/sites/dfiles/Main/documents/hudrss.xml,
https://www.huduser.gov/rss/pub.xml,
https://www.usda.gov/rss-feeds,
https://appraisersblogs.com/feed
    ]
    
    # Process feeds and get new items
    processed_items: List[RSSItem] = fetch_and_process_feeds(feeds)
    print(f"Found {len(processed_items)} new items")
    
    # Send items to Wix API
    if processed_items:
        result: Dict[str, Any] = _send_to_wix_api(processed_items)
        print(f"Sent {result.get('sent_count', 0)} items to Wix")
        return result
    else:
        print("No new items to send to Wix")
        return {"sent_count": 0, "results": []}

# Function for command-line execution
def run_feed_automation() -> None:
    """Run the feed automation from command line"""
    print("Starting RSS feed automation...")
    result: Dict[str, Any] = run_daily_rss_to_wix()
    print(f"Completed RSS feed automation. Processed {result.get('sent_count', 0)} items.")

# This will execute automatically when the script is run by GitHub Actions
run_feed_automation()
