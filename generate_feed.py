import datetime
import html
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

TARGET_URL = "https://www.financialexpress.com/latest-news/"

def main():
    print("Launching headless browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        # Navigate to target page and wait for DOM content
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)
        content = page.content()
        browser.close()

    soup = BeautifulSoup(content, "html.parser")

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

        link = a.get("href").strip()
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

    fg.rss_file("feed.xml", pretty=True)
    print(f"SUCCESS: Generated feed.xml with {count} live articles via Playwright.")

if __name__ == "__main__":
    main()
