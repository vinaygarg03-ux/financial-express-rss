import os
import time
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from email.utils import formatdate

WORKER_URL = "https://quiet-salad-e40e.vinay-garg03.workers.dev/"
FEED_FILE = "feed.xml"
MAX_ITEMS = 500

def parse_existing_feed():
    items = []
    if not os.path.exists(FEED_FILE):
        return items
    try:
        tree = ET.parse(FEED_FILE)
        root = tree.getroot()
        channel = root.find("channel")
        if channel is None:
            return items
        for item in channel.findall("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            guid = item.findtext("guid", link)
            pub_date = item.findtext("pubDate", "")
            description = item.findtext("description", "")
            if link:
                items.append({
                    "title": title,
                    "link": link,
                    "guid": guid,
                    "pubDate": pub_date,
                    "description": description
                })
    except Exception as e:
        print(f"Notice: Could not parse existing feed.xml: {e}")
    return items

def main():
    ts = int(time.time())
    request_url = f"{WORKER_URL}?t={ts}"
    print(f"Fetching live articles: {request_url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(request_url, headers=headers, timeout=25)
        res.raise_for_status()
        posts = res.json()
    except Exception as e:
        print(f"Fetch error: {e}")
        return

    if not isinstance(posts, list) or len(posts) == 0:
        print("No new posts returned.")
        return

    existing_items = parse_existing_feed()
    seen_links = set()
    combined_items = []

    # Add freshly fetched articles
    for post in posts:
        link = post.get("link", "").strip()
        if not link or link in seen_links:
            continue
        seen_links.add(link)
        combined_items.append({
            "title": post.get("title", ""),
            "link": link,
            "guid": link,
            "pubDate": formatdate(time.time(), usegmt=True),
            "description": post.get("description", post.get("summary", ""))
        })

    # Append older preserved articles from previous runs
    for item in existing_items:
        link = item.get("link", "")
        if link and link not in seen_links:
            seen_links.add(link)
            combined_items.append(item)

    # Trim to maximum rolling backlog of 500
    trimmed_items = combined_items[:MAX_ITEMS]

    # Generate standard RSS XML
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Financial Express Live"
    ET.SubElement(channel, "link").text = "https://www.financialexpress.com/"
    ET.SubElement(channel, "description").text = "Financial Express Live News Updates"
    ET.SubElement(channel, "lastBuildDate").text = formatdate(time.time(), usegmt=True)

    for item_data in trimmed_items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = item_data["title"]
        ET.SubElement(item, "link").text = item_data["link"]
        guid = ET.SubElement(item, "guid")
        guid.text = item_data["guid"]
        ET.SubElement(item, "pubDate").text = item_data["pubDate"]
        ET.SubElement(item, "description").text = item_data["description"]

    xml_str = ET.tostring(rss, encoding="utf-8")
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="utf-8")

    with open(FEED_FILE, "wb") as f:
        f.write(pretty_xml)

    print(f"Successfully updated {FEED_FILE} with {len(trimmed_items)} articles.")

if __name__ == "__main__":
    main()
