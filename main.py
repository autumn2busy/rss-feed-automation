import os
import json
import hashlib
import re
import feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
from markdownify import markdownify

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

class RSSItem:
    """Represents a processed RSS feed item"""
    def __init__(self, title, description, link, pub_date=None, image_url=None, source="", item_id=""):
        self.title = title
        self.description = description
        self.link = link
        self.pub_date = pub_date
        self.image_url = image_url
        self.source = source
        self.item_id = item_id
    
    def to_dict(self):
        return {
            'title': self.title,
            'description': self.description,
            'link': self.link,
            'pub_date': self.pub_date.isoformat() if self.pub_date else None,
            'image_url': self.image_url,
            'source': self.source,
            'item_id': self.item_id
        }

def extract_image_url(item_description):
    """Extract image URL from description if available"""
    if not item_description:
        return None
    
    # Parse HTML
    soup = BeautifulSoup(item_description, 'html.parser')
    
    # Look for image tags
    img_tag = soup.find('img')
    if img_tag and img_tag.get('src'):
        return img_tag['src']
    
    return None

def fetch_and_process_feeds():
    """Fetch all RSS feeds and process them into a standard format"""
    # List of RSS feed URLs to process
    feeds = [
        "https://www.nationalmortgagenews.com/feed",
        "https://themreport.com/feed",
        "https://www.valuewalk.com/feed/",
        "https://www.attomdata.com/news/feed/"
    ]
    
    # Get items from all feeds
    all_items = []
    
    for feed_url in feeds:
        try:
            # Get the feed items
            parsed_feed = feedparser.parse(feed_url)
            source_name = feed_url.split('/')[2]  # Extract domain as source name
            
            # Process each item
            for entry in parsed_feed.entries:
                # Create a unique ID for the item based on title and link
                item_hash = hashlib.md5(f"{entry.title}:{entry.link}".encode()).hexdigest()
                
                # Parse the publication date
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                
                # Get description
                description = ""
                if hasattr(entry, 'description'):
                    description = entry.description
                elif hasattr(entry, 'summary'):
                    description = entry.summary
                    
                # Extract image URL if available
                image_url = extract_image_url(description)
                
                # Create clean description (convert HTML to markdown)
                clean_description = markdownify(description)
                
                # Add processed item to our list
                processed_item = RSSItem(
                    title=entry.title,
                    description=clean_description,
                    link=entry.link,
                    pub_date=pub_date,
                    image_url=image_url,
                    source=source_name,
                    item_id=item_hash
                )
                all_items.append(processed_item)
                
        except Exception as e:
            print(f"Error processing feed {feed_url}: {str(e)}")
    
    # Sort items by publication date (newest first)
    all_items.sort(key=lambda x: x.pub_date if x.pub_date else datetime.min, reverse=True)
    
    return all_items

def get_new_items(items, since):
    """Filter items to only get new ones published after a specific date"""
    new_items = []
    
    for item in items:
        # If the item has no pub_date, we can't determine if it's new
        if not item.pub_date:
            continue
            
        # If the item was published after our cutoff date, it's new
        if item.pub_date > since:
            new_items.append(item)
    
    return new_items

def save_last_run_info(last_run_time, last_item_ids):
    """Save information about this run for future reference"""
    save_data = {
        "last_run": last_run_time.isoformat(),
        "last_item_ids": last_item_ids
    }
    
    # Save the data to a JSON file
    with open('data/last_run_info.json', 'w') as f:
        json.dump(save_data, f, indent=2)

def load_last_run_info():
    """Load information about the last run"""
    try:
        # Check if the file exists
        if not os.path.exists('data/last_run_info.json'):
            print("No last run information found, treating all items as new")
            return None, []
            
        # Load the file
        with open('data/last_run_info.json', 'r') as f:
            data = json.load(f)
        
        last_run = datetime.fromisoformat(data["last_run"])
        last_item_ids = data["last_item_ids"]
        
        print(f"Loaded last run information: {last_run}, {len(last_item_ids)} items")
        return last_run, last_item_ids
        
    except Exception as e:
        print(f"Error loading last run information: {str(e)}")
        return None, []

def save_items_to_files(items, all_items=None):
    """Save the items to various formats for easy consumption"""
    
    # Save JSON file with all new items
    items_json = [item.to_dict() for item in items]
    with open('data/new_items.json', 'w') as f:
        json.dump(items_json, f, indent=2)
    
    # Save CSV file with all new items
    if items:
        with open('data/new_items.csv', 'w', newline='', encoding='utf-8') as f:
            # Get field names from first item
            fieldnames = items[0].to_dict().keys()
            
            # Create CSV writer
            import csv
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header and rows
            writer.writeheader()
            for item in items:
                writer.writerow(item.to_dict())
    
    # Save full feed JSON (all items)
    if all_items:
        all_items_json = [item.to_dict() for item in all_items]
        with open('data/all_items.json', 'w') as f:
            json.dump(all_items_json, f, indent=2)
    
    # Create a simple HTML page
    html_content = """
    <!DOCTYPE html>

<head>
    <title>Latest Mortgage Industry News</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
        .item { margin-bottom: 30px; border-bottom: 1px solid #eee; padding-bottom: 20px; }
        .title { font-size: 22px; font-weight: bold; margin-bottom: 10px; }
        .meta { font-size: 14px; color: #666; margin-bottom: 10px; }
        .image { max-width: 100%; margin: 10px 0; }
        .description { line-height: 1.5; }
        .link { margin-top: 15px; }
        .link a { color: #0066cc; text-decoration: none; }
        .link a:hover { text-decoration: underline; }
        .updated { text-align: center; margin-top: 30px; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <h1>Latest Mortgage Industry News</h1>
"""

for item in items:
    pub_date_str = item.pub_date.strftime('%Y-%m-%d %H:%M:%S') if item.pub_date else 'Unknown date'
    
    html_content += f"""
    <div class="item">
        <div class="title">{item.title}</div>
        <div class="meta">Source: {item.source} | Published: {pub_date_str}</div>
    """
    
    if item.image_url:
        html_content += f'<div><img class="image" src="{item.image_url}" alt="{item.title}"></div>'
    
    html_content += f"""
        <div class="description">{item.description}</div>
        <div class="link"><a href="{item.link}" target="_blank">Read More →</a></div>
    </div>
    """

html_content += f"""
    <div class="updated">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
</body>

"""

with open('data/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
def main():
"""Main function to run the RSS feed automation"""
print("Starting RSS feed automation")

# Get the current time to use as this run's timestamp
current_time = datetime.now()

# Get information about the last run
last_run_time, last_item_ids = load_last_run_info()

# Default to 24 hours ago if no last run information
if not last_run_time:
    last_run_time = current_time - timedelta(days=1)
    print(f"Using default cutoff time: {last_run_time}")

# Fetch and process all feed items
all_items = fetch_and_process_feeds()

# Get only the new items
new_items = get_new_items(all_items, last_run_time)
print(f"Found {len(new_items)} new items out of {len(all_items)} total items")

# Filter out items we've already processed (by ID)
filtered_new_items = [item for item in new_items if item.item_id not in last_item_ids]
print(f"After filtering already processed items: {len(filtered_new_items)} items to process")

# Track item IDs we've processed
new_item_ids = last_item_ids.copy()  # Start with existing IDs
for item in filtered_new_items:
    new_item_ids.append(item.item_id)

# Save the items to various formats
save_items_to_files(filtered_new_items, all_items)

# Save information about this run
save_last_run_info(current_time, new_item_ids)

print("RSS feed automation completed successfully")
print(f"Files created in data/ directory:")
print("- new_items.json - JSON array of new items")
print("- new_items.csv - CSV file of new items for import")
print("- all_items.json - JSON array of all items")
print("- index.html - Static HTML page of new items")
if name == "main":
main()

