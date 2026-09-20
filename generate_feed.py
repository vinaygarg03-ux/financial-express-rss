import datetime
import html
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

TARGET_URL = "https://www.financialexpress.com/latest-news/"
# Route through Google's official translate mirror to access the page via Google crawler IPs
PROXY_URL = "https://www-financialexpress-com.translate.goog/latest-news/?_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def clean_url(url):
    """Strip Google Translate tracking parameters and restore original URL."""
    if not url:
        return ""
    if "_x_tr" in url:
        url = url.split("?")[0].replace("-translate-goog", "").replace("www-financialexpress-com", "www.financialexpress.com")
    if url.startswith("https://www.google.com/url?q="):
        url = url.split("https://www.google.com/url?q=")[1].split("&")[0]
    return url

def main():
    print("Fetching via Google Proxy Mirror...")
    res = requests.get(PROXY_URL, headers=HEADERS, timeout=25)
    res.raise_for_status()
    
    soup = BeautifulSoup(res.text, "html.parser")

    fg = FeedGenerator()
    fg.id(TARGET_URL)
    fg.title("Financial Express - Latest News")
    fg.link(href=TARGET_URL, rel="alternate")
    fg.description("Real-time breaking news from Financial Express.")
    fg.language("en")
    fg.lastBuildDate(datetime.datetime.now(datetime.timezone.utc))

    seen = set()
    count = 0

    for div in soup.select("div.entry-title"):
        a = div.find("a")
        if not a or not a.get("href"):
            continue

        raw_link = a.get("href").strip()
        link = clean_url(raw_link)
        title = a.get_text(strip=True)

        if not title or link in seen:
            continue

        if link.startswith("/"):
            link = "https://www.financialexpress.com" + link

        seen.add(link)
        count += 1

        article = div.find_parent("article")
        desc = title
        pub_date = None

        if article:
            summary = article.select_one("p, .entry-summary, .post-excerpt")
            if summary and summary.get_text(strip=True):
                desc = summary.get_text(strip=True)

            time_tag = article.find("time")
            if time_tag and time_tag.get("datetime"):
                try:
                    pub_date = datetime.datetime.fromisoformat(time_tag.get("datetime").replace("Z", "+00:00"))
                except ValueError:
                    pub_date = datetime.datetime.now(datetime.timezone.utc)

        if not pub_date:
            pub_date = datetime.datetime.now(datetime.timezone.utc)

        fe = fg.add_entry()
        fe.id(link)
        fe.title(title)
        fe.link(href=link)
        fe.description(desc)
        fe.pubDate(pub_date)

    if count == 0:
        print("ERROR: Scraped 0 items. Target structure changed.")
        exit(1)

    fg.rss_file("feed.xml", pretty=True)
    print(f"SUCCESS: Generated feed.xml with {count} items.")

if __name__ == "__main__":
    main()
