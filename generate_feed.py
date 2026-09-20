import datetime
import email.utils
import html
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom
import requests
from bs4 import BeautifulSoup

WORKER_URL = "https://quiet-salad-e40e.vinay-garg03.workers.dev/"
SITE_URL = "https://www.financialexpress.com/latest-news/"

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return html.unescape(soup.get_text(strip=True))

def parse_date(date_str):
    if not date_str:
        return datetime.datetime.now(datetime.timezone.utc)
    try:
        clean = date_str.replace("Z", "")
        dt = datetime.datetime.fromisoformat(clean)
        return dt.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc)

def main():
    ts = int(time.time())
    request_url = f"{WORKER_URL}?t={ts}"
    print(f"Fetching live articles: {request_url}")

    res = requests.get(request_url, timeout=25)
    res.raise_for_status()

    posts = res.json()
    if not isinstance(posts, list) or len(posts) == 0:
        raise RuntimeError("Worker did not return a valid list of posts.")

    seen = set()
    valid_posts = []

    for post in posts:
        link = post.get("link", "").strip()
        raw_title = post.get("title", {}).get("rendered", "")
        title = clean_html(raw_title)

        if not title or not link or link in seen:
            continue
        seen.add(link)

        raw_excerpt = post.get("excerpt", {}).get("rendered", "")
        desc = clean_html(raw_excerpt) if raw_excerpt else title

        # Financial Express date_gmt is in UTC
        raw_date = post.get("date_gmt") or post.get("date") or ""
        pub_date = parse_date(raw_date)

        valid_posts.append({
            "id": link,
            "title": title,
            "link": link,
            "description": desc,
            "pubDate": pub_date
        })

    # Sort strictly: largest timestamp (latest published) at index 0
    valid_posts.sort(key=lambda x: x["pubDate"], reverse=True)

    # Build standard RSS 2.0 XML
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "Financial Express - Latest News"
    ET.SubElement(channel, "link").text = SITE_URL
    ET.SubElement(channel, "description").text = "Real-time breaking business and financial news."
    ET.SubElement(channel, "language").text = "en"
    ET.SubElement(channel, "lastBuildDate").text = email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc))

    for post in valid_posts:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = post["title"]
        ET.SubElement(item, "link").text = post["link"]
        ET.SubElement(item, "guid").text = post["link"]
        ET.SubElement(item, "description").text = post["description"]
        ET.SubElement(item, "pubDate").text = email.utils.format_datetime(post["pubDate"])

    # Format pretty XML
    xml_str = ET.tostring(rss, encoding="utf-8")
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="utf-8")

    with open("feed.xml", "wb") as f:
        f.write(pretty_xml)

    print(f"SUCCESS: Generated feed.xml with {len(valid_posts)} articles sorted newest first.")

if __name__ == "__main__":
    main()
