import os, re, time, requests, html
from datetime import datetime
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom
from email.utils import formatdate

SECTIONS = [
    {
        'tag': 'Review',
        'url': 'https://www.financialexpress.com/auto/reviews/',
        'path_filter': '/auto/reviews/'
    },
    {
        'tag': 'Car News',
        'url': 'https://www.financialexpress.com/auto/car-news/',
        'path_filter': '/auto/car-news/'
    },
    {
        'tag': 'Bike News',
        'url': 'https://www.financialexpress.com/auto/bike-news/',
        'path_filter': '/auto/bike-news/'
    }
]

FEED_FILE = 'auto_feed.xml'
MAX_ITEMS = 400

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def clean_text(text):
    if not text:
        return ''
    clean = re.sub(r'<[^>]+>', '', str(text))
    return html.unescape(clean).strip()

def parse_iso_date(dt_str):
    if not dt_str:
        return time.time()
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.timestamp()
    except Exception:
        return time.time()

def parse_existing_feed():
    items = []
    if not os.path.exists(FEED_FILE):
        return items
    try:
        tree = ET.parse(FEED_FILE)
        root = tree.getroot()
        channel = root.find('channel')
        if channel is None:
            return items
        for item in channel.findall('item'):
            link = clean_text(item.findtext('link', ''))
            if link:
                pub_text = clean_text(item.findtext('pubDate', ''))
                epoch = time.time()
                try:
                    import email.utils
                    epoch = email.utils.mktime_tz(email.utils.parsedate_tz(pub_text))
                except Exception:
                    pass
                items.append({
                    'title': clean_text(item.findtext('title', '')),
                    'link': link,
                    'guid': clean_text(item.findtext('guid', link)),
                    'pubDate': pub_text,
                    'epoch': epoch,
                    'description': clean_text(item.findtext('description', ''))
                })
    except Exception as e:
        print(f'Notice: {e}')
    return items

def scrape_section(sec_info):
    articles = []
    url = sec_info['url']
    path_filter = sec_info['path_filter']
    tag = sec_info['tag']

    print(f'Fetching {tag}: {url}')
    try:
        res = requests.get(url, headers=HEADERS, timeout=25)
        res.raise_for_status()
    except Exception as e:
        print(f'Error fetching {url}: {e}')
        return articles

    soup = BeautifulSoup(res.text, 'html.parser')
    seen = set()

    for art in soup.find_all('article'):
        title_box = art.find('div', class_='entry-title')
        if not title_box:
            continue
        a_tag = title_box.find('a', href=True)
        if not a_tag:
            continue

        href = a_tag['href'].strip()
        if path_filter not in href:
            continue
        clean_url = href.split('?')[0].rstrip('/')
        if clean_url in seen:
            continue

        title = clean_text(a_tag.get_text())
        if not title or len(title) < 15:
            continue

        time_tag = art.find('time')
        epoch_val = time.time()
        if time_tag and time_tag.get('datetime'):
            epoch_val = parse_iso_date(time_tag['datetime'])

        desc = title
        p_desc = art.find('p')
        if p_desc and p_desc.get_text().strip() != title:
            desc = clean_text(p_desc.get_text())

        seen.add(clean_url)
        articles.append({
            'title': f'[{tag}] {title}',
            'link': clean_url,
            'guid': clean_url,
            'epoch': epoch_val,
            'pubDate': formatdate(epoch_val, usegmt=True),
            'description': desc
        })

    print(f'  Found {len(articles)} articles in {tag}')
    return articles

def main():
    fresh_items = []
    for sec in SECTIONS:
        sec_items = scrape_section(sec)
        fresh_items.extend(sec_items)

    print(f'Total fresh articles: {len(fresh_items)}')
    if not fresh_items:
        return

    # Clear existing feed on local disk to flush identical timestamps
    if os.path.exists(FEED_FILE):
        try:
            os.remove(FEED_FILE)
        except Exception:
            pass

    # Sort strictly by real publication timestamp (newest first)
    fresh_items.sort(key=lambda x: x.get('epoch', 0), reverse=True)
    trimmed = fresh_items[:MAX_ITEMS]

    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = 'Financial Express - Automotive Hub'
    ET.SubElement(channel, 'link').text = 'https://www.financialexpress.com/auto/'
    ET.SubElement(channel, 'description').text = 'Combined Reviews, Car News, and Bike News from Financial Express'
    ET.SubElement(channel, 'lastBuildDate').text = formatdate(time.time(), usegmt=True)

    for it in trimmed:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = it['title']
        ET.SubElement(item, 'link').text = it['link']
        guid = ET.SubElement(item, 'guid')
        guid.text = it['guid']
        ET.SubElement(item, 'pubDate').text = it['pubDate']
        ET.SubElement(item, 'description').text = it['description']

    xml_str = ET.tostring(rss, encoding='utf-8')
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent='  ', encoding='utf-8')

    with open(FEED_FILE, 'wb') as f:
        f.write(pretty_xml)

    print(f'Success: Updated {FEED_FILE} with {len(trimmed)} chronologically sorted articles.')

if __name__ == '__main__':
    main()
