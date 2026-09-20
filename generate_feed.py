import datetime
import html
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

# Fetch 50 items so both sidebar stream and main stream are fully populated
API_URL = "https://www.financialexpress.com/wp-json/wp/v2/posts?per_page=50&_fields=id,date_gmt,link,title,excerpt,categories"
SITE_URL = "https://www.financialexpress.com/latest-news/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return html.unescape(soup.get_text(strip=True))

def main():
    res = requests.get(API_URL, headers=HEADERS, timeout=20)
    res.raise_for_status()
    posts = res.json()

    fg = FeedGenerator()
    fg.id(SITE_URL)
    fg.title("Financial Express - Latest News")
    fg.link(href=SITE_URL, rel="alternate")
    fg.description("Real-time breaking news from Financial Express.")
    fg.language("en")
    fg.lastBuildDate(datetime.datetime.now(datetime.timezone.utc))

    seen = set()
    count = 0

    for post in posts:
        link = post.get("link", "").strip()
        raw_title = post.get("title", {}).get("rendered", "")
        title = clean_html(raw_title)

        if not title or not link or link in seen:
            continue
        seen.add(link)

        raw_excerpt = post.get("excerpt", {}).get("rendered", "")
        desc = clean_html(raw_excerpt) if raw_excerpt else title

        date_str = post.get("date_gmt", "")
        pub_date = None
        if date_str:
            try:
                pub_date = datetime.datetime.fromisoformat(date_str).replace(tzinfo=datetime.timezone.utc)
            except Exception:
                pub_date = datetime.datetime.now(datetime.timezone.utc)
        if not pub_date:
            pub_date = datetime.datetime.now(datetime.timezone.utc)

        fe = fg.add_entry()
        fe.id(link)
        fe.title(title)
        fe.link(href=link)
        fe.description(desc)
        fe.pubDate(pub_date)
        count += 1

    fg.rss_file("feed.xml", pretty=True)
    print(f"SUCCESS: Generated feed.xml with {count} items.")

if __name__ == "__main__":
    main()
