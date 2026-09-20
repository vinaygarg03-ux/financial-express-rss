import datetime
import requests
import xml.etree.ElementTree as ET
from feedgen.feed import FeedGenerator

FEED_SOURCE = "https://news.google.com/rss/search?q=site:financialexpress.com&hl=en-IN&gl=IN&ceid=IN:en"
TARGET_URL = "https://www.financialexpress.com/latest-news/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml"
}

def main():
    res = requests.get(FEED_SOURCE, headers=HEADERS, timeout=20)
    res.raise_for_status()

    root = ET.fromstring(res.content)
    channel = root.find("channel")

    fg = FeedGenerator()
    fg.id(TARGET_URL)
    fg.title("Financial Express - Latest News")
    fg.link(href=TARGET_URL, rel="alternate")
    fg.description("Latest news stories from Financial Express.")
    fg.language("en")
    fg.lastBuildDate(datetime.datetime.now(datetime.timezone.utc))

    items = channel.findall("item") if channel is not None else []
    count = 0

    for item in items[:25]:
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        pub_el = item.find("pubDate")

        if title_el is None or not title_el.text:
            continue

        raw_title = title_el.text.strip()
        # Clean title by removing source suffix if appended by Google News
        if " - Financial Express" in raw_title:
            raw_title = raw_title.replace(" - Financial Express", "").strip()

        link = link_el.text.strip() if link_el is not None and link_el.text else TARGET_URL
        desc = desc_el.text.strip() if desc_el is not None and desc_el.text else raw_title

        pub_date = None
        if pub_el is not None and pub_el.text:
            try:
                # Parse RFC 822 format (e.g., "Sun, 20 Sep 2026 10:15:00 GMT")
                pub_date = datetime.datetime.strptime(pub_el.text.strip(), "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=datetime.timezone.utc)
            except Exception:
                pub_date = datetime.datetime.now(datetime.timezone.utc)

        if not pub_date:
            pub_date = datetime.datetime.now(datetime.timezone.utc)

        fe = fg.add_entry()
        fe.id(link)
        fe.title(raw_title)
        fe.link(href=link)
        fe.description(desc)
        fe.pubDate(pub_date)
        count += 1

    fg.rss_file("feed.xml", pretty=True)
    print(f"SUCCESS: Generated feed.xml with {count} items from syndicated stream.")

if __name__ == "__main__":
    main()
