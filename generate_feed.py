import datetime
import time
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

BASE_URL = "https://www.financialexpress.com/latest-news/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
}

def build_rss_feed():
    fg = FeedGenerator()
    fg.id(BASE_URL)
    fg.title("Financial Express - Latest News")
    fg.author({"name": "Financial Express Scraper"})
    fg.link(href=BASE_URL, rel="alternate")
    fg.description("Latest news stories from Financial Express main feed.")
    fg.language("en")

    # Add timestamp parameter to bypass server/CDN caching
    cache_buster_url = f"{BASE_URL}?_cb={int(time.time())}"

    try:
        response = requests.get(cache_buster_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")

    seen_links = set()
    items_count = 0

    title_blocks = soup.select("div.entry-title")

    for block in title_blocks:
        link_tag = block.find("a")
        if not link_tag or not link_tag.get("href"):
            continue

        url = link_tag.get("href").strip()
        title = link_tag.get_text(strip=True)

        if not title or url in seen_links:
            continue

        if url.startswith("/"):
            url = "https://www.financialexpress.com" + url

        seen_links.add(url)
        items_count += 1

        article = block.find_parent("article")
        description = title
        pub_date = None

        if article:
            summary_tag = article.select_one("p, .entry-summary, .post-excerpt")
            if summary_tag and summary_tag.get_text(strip=True):
                description = summary_tag.get_text(strip=True)

            time_tag = article.find("time")
            if time_tag and time_tag.get("datetime"):
                try:
                    pub_date = datetime.datetime.fromisoformat(
                        time_tag.get("datetime").replace("Z", "+00:00")
                    )
                except ValueError:
                    pub_date = datetime.datetime.now(datetime.timezone.utc)

        if not pub_date:
            pub_date = datetime.datetime.now(datetime.timezone.utc)

        fe = fg.add_entry()
        fe.id(url)
        fe.title(title)
        fe.link(href=url)
        fe.description(description)
        fe.pubDate(pub_date)

    fg.rss_file("feed.xml", pretty=True)
    print(f"Successfully generated feed.xml with {items_count} main feed stories.")

if __name__ == "__main__":
    build_rss_feed()