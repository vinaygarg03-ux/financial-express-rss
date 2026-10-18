import os, re, time, requests, html
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
                items.append({
                    'title': clean_text(item.findtext('title', '')),
                    'link': link,
                    'guid': clean_text(item.findtext('guid', link)),
                    'pubDate': clean_text(item.findtext('pubDate', '')),
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

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if path_filter not in href:
            continue
        clean_url = href.split('?')[0].rstrip('/')
        if clean_url in ['https://www.financialexpress.com' + path_filter.rstrip('/'), 'http://www.financialexpress.com' + path_filter.rstrip('/')]:
            continue
        if '/photos/' in clean_url or '/page/' in clean_url or clean_url in seen:
            continue

        title = clean_text(a.get_text())
        if not title or len(title) < 20 or 'PHOTOS' in title:
            continue

        desc = title
        parent = a.find_parent(['article', 'li', 'div'])
        if parent:
            p_elem = parent.find(['p', 'span'])
            if p_elem and p_elem.get_text().strip() != title:
                desc = clean_text(p_elem.get_text())

        seen.add(clean_url)
        articles.append({
            'title': f'[{tag}] {title}',
            'link': clean_url,
            'guid': clean_url,
            'pubDate': formatdate(time.time(), usegmt=True),
            'description': desc
        })

    print(f'  Found {len(articles)} articles in {tag}')
    return articles

def main():
    fresh_items = []
    for sec in SECTIONS:
        sec_items = scrape_section(sec)
        fresh_items.extend(sec_items)

    print(f'Total fresh automotive articles: {len(fresh_items)}')
    if not fresh_items:
        return

    existing = parse_existing_feed()
    combined = []
    final_seen = set()

    for it in fresh_items:
        if it['link'] not in final_seen:
            final_seen.add(it['link'])
            combined.append(it)

    for it in existing:
        if it['link'] not in final_seen:
            final_seen.add(it['link'])
            combined.append(it)

    trimmed = combined[:MAX_ITEMS]

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

    print(f'Success: Updated {FEED_FILE} with {len(trimmed)} total articles.')

if __name__ == '__main__':
    main()
