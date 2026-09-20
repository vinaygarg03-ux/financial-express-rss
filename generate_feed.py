import datetime
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

URL = "https://www.financialexpress.com/latest-news/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

def main():
    r = requests.get(URL, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    fg = FeedGenerator()
    fg.id(URL)
    fg.title("Financial Express - Latest News")
    fg.link(href=URL, rel="alternate")
    fg.description("Latest news stories from Financial Express.")
    fg.language("en")
    fg.lastBuildDate(datetime.datetime.now(datetime.timezone.utc))

    seen = set()
    entries = []

    for div in soup.select("div.entry-title"):
        a = div.find("a")
        if not a or not a.get("href"):
            continue
        link = a.get("href").strip()
        title = a.get_text(strip=True)
        if not title or link in seen:
            continue
        if link.startswith("/"):
            link = "https://www.financialexpress.com" + link
        seen.add(link)

        article = div.find_parent("article")
        desc = title
        if article:
            summary = article.select_one("p, .entry-summary, .post-excerpt")
            if summary and summary.get_text(strip=True):
                desc = summary.get_text(strip=True)

        entries.append({
            "title": title,
            "link": link,
            "description": desc
        })

    # Add entries in reverse order so the freshest items in the main stream sit on top
    for item in entries[::-1]:
        fe = fg.add_entry()
        fe.id(item["link"])
        fe.title(item["title"])
        fe.link(href=item["link"])
        fe.description(item["description"])
        fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

    fg.rss_file("feed.xml", pretty=True)
    print(f"Generated feed.xml with {len(entries)} items (freshest prioritized).")

if __name__ == "__main__":
    main()
