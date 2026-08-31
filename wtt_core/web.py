import sys
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import html2text

class WebPageFetcher:
    """Fetches standard web pages and JS-rendered pages."""

    @staticmethod
    def fetch_with_playwright(url: str) -> tuple[str, str]:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(1500)
                title = page.title()
                html_content = page.content()
                browser.close()
                return html_content, title
        except Exception as e:
            print(f"⚠️ Playwright notice: {e}", file=sys.stderr)
            return "", ""

    @classmethod
    def fetch_page(cls, url: str, session: requests.Session, force_js: bool = False) -> dict:
        html_content = ""
        title = ""

        if force_js:
            print(f"🎭 [wtt] Force rendering with Playwright Headless Chromium...")
            html_content, title = cls.fetch_with_playwright(url)

        if not html_content:
            r = session.get(url, timeout=12)
            r.raise_for_status()
            html_content = r.text

            is_spa_shell = ("<div id=\"root\"></div>" in html_content or 
                            "<div id=\"app\"></div>" in html_content or 
                            "<div id=\"__next\"></div>" in html_content and len(html_content) < 3000)

            if is_spa_shell:
                print(f"⚡ [wtt] SPA JS shell detected! Switching to Playwright rendering...")
                js_html, js_title = cls.fetch_with_playwright(url)
                if js_html:
                    html_content = js_html
                    title = js_title

        soup = BeautifulSoup(html_content, 'html.parser')

        if not title:
            title = soup.title.string.strip() if soup.title and soup.title.string else url

        meta_desc = ""
        desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if desc_tag and desc_tag.get('content'):
            meta_desc = desc_tag['content'].strip()

        headings = []
        for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            text = h.get_text().strip()
            if text:
                headings.append({'level': h.name, 'text': text})

        links = []
        for a in soup.find_all('a', href=True):
            link_text = a.get_text().strip()
            href = urljoin(url, a['href'])
            if link_text and href.startswith(('http://', 'https://')):
                links.append({'text': link_text, 'href': href})

        prettified_html = soup.prettify()

        soup_copy = BeautifulSoup(html_content, 'html.parser')
        for elem in soup_copy(['script', 'style', 'nav', 'footer', 'svg', 'noscript']):
            elem.decompose()

        h2t = html2text.HTML2Text()
        h2t.ignore_links = False
        h2t.ignore_images = True
        h2t.body_width = 0
        markdown_content = h2t.handle(str(soup_copy))

        clean_text = soup_copy.get_text(separator='\n').strip()
        clean_lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        clean_text = '\n'.join(clean_lines)

        return {
            'url': url,
            'title': title,
            'description': meta_desc,
            'headings': headings,
            'markdown': markdown_content,
            'clean_text': clean_text,
            'html': prettified_html,
            'links': links[:30]
        }
