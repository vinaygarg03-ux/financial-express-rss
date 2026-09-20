import datetime
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

TARGET_URL = "https://www.financialexpress.com/latest-news/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

def build_rss_feed():
    fg = FeedGenerator()
    fg.id(TARGET_URL)
    fg.title("Financial Express - Latest News")
    fg.author({"name": "Financial Express Scraper"})
    fg.link(href=TARGET_URL, rel="alternate")
    fg.description("Latest news and real-time updates from Financial Express.")
    fg.language("en")

    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")
    articles = soup.select("div.post-content, article, div.entry-wrapper")
    seen_links = set()

    for item in articles:
        link_tag = item.select_one("h2 a, h3 a, a.entry-title")
        if not link_tag or not link_tag.get("href"):
            continue

        url = link_tag.get("href").strip()
        title = link_tag.get_text(strip=True)

        if not title or url in seen_links:
            continue

        seen_links.add(url)

        summary_tag = item.select_one("p, div.post-excerpt")
        description = summary_tag.get_text(strip=True) if summary_tag else title

        time_tag = item.select_one("time, span.post-date, div.post-date")
        pub_date = None
        if time_tag:
            datetime_attr = time_tag.get("datetime")
            if datetime_attr:
                try:
                    pub_date = datetime.datetime.fromisoformat(datetime_attr.replace("Z", "+00:00"))
                except ValueError:
                    pub_date = datetime.datetime.now(datetime.timezone.utc)
            else:
                pub_date = datetime.datetime.now(datetime.timezone.utc)
        else:
            pub_date = datetime.datetime.now(datetime.timezone.utc)

        fe = fg.add_entry()
        fe.id(url)
        fe.title(title)
        fe.link(href=url)
        fe.description(description)
        fe.pubDate(pub_date)

    fg.rss_file("feed.xml", pretty=True)
    print(f"Successfully generated feed.xml with {len(seen_links)} items.")

if __name__ == "__main__":
    build_rss_feed()
