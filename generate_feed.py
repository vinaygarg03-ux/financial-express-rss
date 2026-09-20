import datetime
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

TARGET_URL = "https://www.financialexpress.com/latest-news/"

def main():
    print("Launching stealth browser...")
    with sync_playwright() as p:
        # Launch with flags that mask automated browser fingerprints
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-US"
        )
        page = context.new_page()

        # Mask navigator.webdriver
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        print(f"Loading {TARGET_URL}...")
        page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)

        # Wait until article elements actually populate
        try:
            page.wait_for_selector("div.entry-title", timeout=15000)
        except Exception:
            print("Warning: Selector wait timed out, proceeding to parse DOM...")

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

    if count == 0:
        print("ERROR: Scraped 0 items. Cloudflare or DOM mismatch. Aborting feed deployment.")
        sys.exit(1)

    fg.rss_file("feed.xml", pretty=True)
    print(f"SUCCESS: Generated feed.xml with {count} items.")

if __name__ == "__main__":
    main()
