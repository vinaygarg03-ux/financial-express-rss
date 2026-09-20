import datetime
import sys
from seleniumbase import Driver
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

TARGET_URL = "https://www.financialexpress.com/latest-news/"

def main():
    print("Launching Undetected Chrome (UC Mode)...")
    # Launch Chrome with undetected-chromedriver and headless UC mode
    driver = Driver(uc=True, headless=True)

    try:
        print(f"Navigating to {TARGET_URL}...")
        driver.uc_open_with_reconnect(TARGET_URL, reconnect_time=6)

        # Wait for article title element to appear
        driver.wait_for_element_present("div.entry-title", timeout=25)
        html = driver.page_source
    except Exception as e:
        print("Wait encountered notice:", e)
        html = driver.page_source
    finally:
        driver.quit()

    soup = BeautifulSoup(html, "html.parser")

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
        print("ERROR: Scraped 0 items. Cloudflare or DOM mismatch.")
        sys.exit(1)

    fg.rss_file("feed.xml", pretty=True)
    print(f"SUCCESS: Generated feed.xml with {count} items.")

if __name__ == "__main__":
    main()
