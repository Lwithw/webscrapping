import sys
import os
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

visited = set()
assets_visited = set()

DOWNLOAD_DIR = 'downloaded_site'

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

# Helper to create local file path
def get_local_path(url, base_url):
    parsed = urlparse(url)
    base_parsed = urlparse(base_url)
    path = parsed.path
    if path.endswith('/') or path == '':
        path += 'index.html'
    if path.startswith('/'):
        path = path[1:]
    local_path = os.path.join(DOWNLOAD_DIR, path)
    return local_path

# Helper to save content to file
def save_file(content, local_path, mode='wb'):
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, mode) as f:
        f.write(content)

# Download and save asset (CSS, JS, images, fonts)
def download_asset(asset_url, base_url):
    if asset_url in assets_visited:
        return
    assets_visited.add(asset_url)
    try:
        r = requests.get(asset_url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            local_path = get_local_path(asset_url, base_url)
            save_file(r.content, local_path)
            print(f'Downloaded: {asset_url}')
    except Exception as e:
        print(f'Failed to download asset {asset_url}: {e}')

# Extract font URLs from CSS content
def extract_font_urls(css_content, base_url):
    font_urls = []
    # Find @font-face rules
    font_face_pattern = r'@font-face\s*{[^}]*url\(["\']?([^"\')\s]+)["\']?[^}]*}'
    matches = re.findall(font_face_pattern, css_content, re.IGNORECASE | re.DOTALL)
    for match in matches:
        font_url = urljoin(base_url, match)
        font_urls.append(font_url)
    return font_urls

# Download Font Awesome and other icon fonts
def download_font_assets(base_url):
    # Common Font Awesome CDN URLs
    font_awesome_urls = [
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.ttf',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.ttf',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.ttf'
    ]
    
    for font_url in font_awesome_urls:
        download_asset(font_url, base_url)

# Crawl and download HTML pages
def crawl(url, base_url):
    if url in visited:
        return
    visited.add(url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return
        soup = BeautifulSoup(r.text, 'lxml')
        local_path = get_local_path(url, base_url)
        save_file(r.content, local_path)
        print(f'Downloaded page: {url}')
        
        # Download assets
        for tag, attr in [('img', 'src'), ('link', 'href'), ('script', 'src')]:
            for el in soup.find_all(tag):
                asset = el.get(attr)
                if not asset:
                    continue
                asset_url = urljoin(url, asset)
                if urlparse(asset_url).netloc == urlparse(base_url).netloc:
                    download_asset(asset_url, base_url)
        
        # Download CSS files and extract font URLs
        for link in soup.find_all('link', rel='stylesheet'):
            css_url = link.get('href')
            if css_url:
                css_url = urljoin(url, css_url)
                if urlparse(css_url).netloc == urlparse(base_url).netloc:
                    try:
                        css_r = requests.get(css_url, headers=HEADERS, timeout=10)
                        if css_r.status_code == 200:
                            local_css_path = get_local_path(css_url, base_url)
                            save_file(css_r.content, local_css_path)
                            print(f'Downloaded CSS: {css_url}')
                            
                            # Extract and download fonts from CSS
                            font_urls = extract_font_urls(css_r.text, css_url)
                            for font_url in font_urls:
                                download_asset(font_url, base_url)
                    except Exception as e:
                        print(f'Failed to download CSS {css_url}: {e}')
        
        # Find and crawl internal links
        for a in soup.find_all('a', href=True):
            link = urljoin(url, a['href'])
            if urlparse(link).netloc == urlparse(base_url).netloc:
                if '#' in link:
                    link = link.split('#')[0]
                if link not in visited:
                    crawl(link, base_url)
    except Exception as e:
        print(f'Failed to crawl {url}: {e}')

def main():
    if len(sys.argv) < 2:
        print('Usage: python scraper.py <website_url>')
        return
    url = sys.argv[1]
    print(f'Starting to scrape: {url}')
    
    # Download Font Awesome assets first
    print('Downloading Font Awesome assets...')
    download_font_assets(url)
    
    # Crawl the website
    crawl(url, url)
    print('Scraping complete. Files saved in', DOWNLOAD_DIR)

if __name__ == '__main__':
    main() 