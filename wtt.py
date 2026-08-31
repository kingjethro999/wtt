#!/usr/bin/env python3
"""
wtt (Web To Text / URL To Text / Web To HTML)
Converts websites/URLs, JS-rendered SPAs, and Swagger/OpenAPI docs into JSON, Markdown, Plain Text, or HTML locally.
"""

import sys
import os
import re
import json
import subprocess
import http.server
import socketserver
import webbrowser
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import html2text

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

class OpenAPIParser:
    """Handles OpenAPI / Swagger UI specs extraction & endpoint matching."""

    @staticmethod
    def is_swagger_url(url: str, html_content: str = "") -> bool:
        lower_url = url.lower()
        if any(k in lower_url for k in ['swagger', 'openapi', 'api-docs', 'redoc']):
            return True
        if html_content:
            lower_html = html_content.lower()
            if any(k in lower_html for k in ['swagger-ui', 'swaggerui', 'swaggerdoc', 'openapi']):
                return True
        return False

    @classmethod
    def extract_spec(cls, url: str, session: requests.Session) -> tuple[dict | None, str | None]:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        init_js_candidates = [
            urljoin(url, "swagger-ui-init.js"),
            urljoin(base_url + parsed.path.rstrip('/') + '/', "swagger-ui-init.js"),
            f"{base_url}/swagger-docs/swagger-ui-init.js",
            f"{base_url}/api-docs/swagger-ui-init.js"
        ]

        for init_url in set(init_js_candidates):
            try:
                r = session.get(init_url, timeout=8)
                if r.status_code == 200 and "swaggerDoc" in r.text:
                    spec = cls._parse_swagger_init_js(r.text)
                    if spec:
                        return spec, init_url
            except Exception:
                pass

        try:
            r = session.get(url, timeout=8)
            if r.status_code == 200:
                html = r.text

                spec_url_match = re.search(r'url\s*:\s*["\']([^"\']+\.json[^"\']*)["\']', html, re.I)
                if spec_url_match:
                    target = urljoin(url, spec_url_match.group(1))
                    spec = cls._fetch_json(target, session)
                    if spec:
                        return spec, target

                if "swagger-ui-init.js" in html:
                    init_target = urljoin(url, "swagger-ui-init.js")
                    r_init = session.get(init_target, timeout=8)
                    if r_init.status_code == 200:
                        spec = cls._parse_swagger_init_js(r_init.text)
                        if spec:
                            return spec, init_target
        except Exception:
            pass

        probes = [
            urljoin(url, "swagger.json"),
            urljoin(url, "openapi.json"),
            urljoin(base_url + parsed.path.rstrip('/') + '/', "swagger.json"),
            urljoin(base_url + parsed.path.rstrip('/') + '/', "openapi.json"),
            f"{base_url}/swagger.json",
            f"{base_url}/openapi.json",
            f"{base_url}/v3/api-docs",
            f"{base_url}/api-docs",
            f"{base_url}/swagger/v1/swagger.json"
        ]

        for probe_url in probes:
            spec = cls._fetch_json(probe_url, session)
            if spec and ("openapi" in spec or "swagger" in spec or "paths" in spec):
                return spec, probe_url

        return None, None

    @staticmethod
    def _fetch_json(url: str, session: requests.Session) -> dict | None:
        try:
            r = session.get(url, timeout=6)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_swagger_init_js(js_text: str) -> dict | None:
        modified_text = js_text.replace('var options =', 'globalThis.options =', 1)
        mock_env = '''
        const SwaggerUIBundle = function(opts) { return {}; };
        SwaggerUIBundle.presets = { apis: {} };
        SwaggerUIBundle.plugins = { DownloadUrl: {} };
        const SwaggerUIStandalonePreset = {};
        const window = { location: { search: '', origin: '' } };
        '''
        js_code = mock_env + modified_text + '\nif (typeof window.onload === "function") window.onload(); console.log(JSON.stringify(globalThis.options ? globalThis.options.swaggerDoc : null));'
        try:
            res = subprocess.run(['node'], input=js_code, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                out = res.stdout.strip()
                if out != "null":
                    return json.loads(out)
        except Exception:
            pass
        return None

    @classmethod
    def match_fragment(cls, spec: dict, fragment: str) -> dict | None:
        if not fragment:
            return None

        clean_frag = fragment.lstrip('#/').rstrip('/')
        parts = [p for p in clean_frag.split('/') if p]
        if not parts:
            return None

        tag = parts[0] if len(parts) > 1 else None
        op_str = parts[-1]

        methods = ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']
        matched_method = None
        calc_path = None

        for m in methods:
            if op_str.lower().startswith(m + '_'):
                matched_method = m
                raw_path_part = op_str[len(m)+1:]
                calc_path = '/' + raw_path_part.replace('_', '/')
                break

        paths = spec.get('paths', {})

        if calc_path and matched_method:
            for p, methods_dict in paths.items():
                if p.lower() == calc_path.lower() and matched_method in methods_dict:
                    return {
                        'path': p,
                        'method': matched_method.upper(),
                        'details': methods_dict[matched_method],
                        'tag': tag
                    }

        for p, methods_dict in paths.items():
            for m, details in methods_dict.items():
                op_id = details.get('operationId', '')
                if op_id and op_id.lower() == op_str.lower():
                    return {
                        'path': p,
                        'method': m.upper(),
                        'details': details,
                        'tag': tag
                    }

        for p, methods_dict in paths.items():
            for m, details in methods_dict.items():
                if matched_method and m.lower() != matched_method.lower():
                    continue
                if all(word in p for word in op_str.split('_') if len(word) > 2 and word not in ['api', 'v1', 'v2', 'post', 'get', 'put']):
                    return {
                        'path': p,
                        'method': m.upper(),
                        'details': details,
                        'tag': tag
                    }

        return None


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


def format_swagger_to_markdown(spec: dict, target_op: dict | None, source_url: str) -> str:
    info = spec.get('info', {})
    lines = []
    lines.append(f"# {info.get('title', 'API Documentation')}")
    if info.get('version'):
        lines.append(f"**Version:** {info.get('version')}")
    if info.get('description'):
        lines.append(f"\n{info.get('description')}\n")
    lines.append(f"**Source URL:** {source_url}\n")
    lines.append("---")

    if target_op:
        lines.append("\n## 🎯 Targeted Operation\n")
        lines.append(f"### `{target_op['method']}` {target_op['path']}")
        details = target_op['details']
        if details.get('summary'):
            lines.append(f"**Summary:** {details['summary']}")
        if details.get('description'):
            lines.append(f"**Description:** {details['description']}")
        if details.get('operationId'):
            lines.append(f"**Operation ID:** `{details['operationId']}`")

        params = details.get('parameters', [])
        if params:
            lines.append("\n#### Parameters")
            lines.append("| Name | In | Required | Type | Description |")
            lines.append("| --- | --- | --- | --- | --- |")
            for p in params:
                name = p.get('name', '')
                p_in = p.get('in', '')
                req = "Yes" if p.get('required') else "No"
                p_type = p.get('schema', {}).get('type', p.get('type', ''))
                desc = p.get('description', '').replace('\n', ' ')
                lines.append(f"| `{name}` | {p_in} | {req} | {p_type} | {desc} |")

        req_body = details.get('requestBody')
        if req_body:
            lines.append("\n#### Request Body")
            if req_body.get('description'):
                lines.append(f"{req_body['description']}")
            content = req_body.get('content', {})
            for ctype, cval in content.items():
                lines.append(f"- **Content-Type:** `{ctype}`")
                schema = cval.get('schema')
                if schema:
                    lines.append("```json")
                    lines.append(json.dumps(schema, indent=2))
                    lines.append("```")

        responses = details.get('responses', {})
        if responses:
            lines.append("\n#### Responses")
            for code, resp in responses.items():
                lines.append(f"- **`{code}`**: {resp.get('description', '')}")
                res_content = resp.get('content', {})
                for ctype, cval in res_content.items():
                    schema = cval.get('schema')
                    if schema:
                        lines.append("```json")
                        lines.append(json.dumps(schema, indent=2))
                        lines.append("```")
        lines.append("\n---\n")

    lines.append("\n## 📋 All Available Endpoints\n")
    paths = spec.get('paths', {})
    for path, methods in paths.items():
        for m, d in methods.items():
            if m.lower() in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                summary = d.get('summary', '') or d.get('description', '')
                lines.append(f"- **`{m.upper()}`** `{path}` - {summary}")

    return '\n'.join(lines)


def convert_url(url: str, fmt: str = "md", target_path: str = ".", force_js: bool = False) -> tuple[str, str, float]:
    """Converts URL and saves file. Returns: (final_file_path, content_preview, file_size_kb)"""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parsed_url = urlparse(url)
    fragment = parsed_url.fragment

    print(f"🌐 [wtt] Fetching URL: {url}")

    spec, spec_url = OpenAPIParser.extract_spec(url, session)

    if spec:
        print(f"⚡ [wtt] Detected OpenAPI/Swagger spec at: {spec_url or url}")
        target_op = OpenAPIParser.match_fragment(spec, fragment)
        if target_op:
            print(f"🎯 [wtt] Matched operation: {target_op['method']} {target_op['path']}")

        if fmt == "json":
            out_data = {
                "source_url": url,
                "spec_url": spec_url,
                "targeted_operation": target_op,
                "info": spec.get("info", {}),
                "spec": spec
            }
            content = json.dumps(out_data, indent=2)
            default_ext = ".json"
        elif fmt == "txt":
            md = format_swagger_to_markdown(spec, target_op, url)
            content = re.sub(r'[#*`|_~-]', '', md)
            default_ext = ".txt"
        elif fmt == "html":
            md = format_swagger_to_markdown(spec, target_op, url)
            content = f"<!DOCTYPE html><html><head><title>{spec.get('info', {}).get('title', 'API Docs')}</title><style>body{{font-family:sans-serif;line-height:1.6;max-width:900px;margin:2rem auto;padding:0 1rem;}}pre{{background:#f4f4f4;padding:1rem;border-radius:6px;overflow-x:auto;}}table{{border-collapse:collapse;width:100%;}}th,td{{border:1px solid #ddd;padding:8px;text-align:left;}}th{{background-f4f4f4;}}</style></head><body><pre>{md}</pre></body></html>"
            default_ext = ".html"
        else: # md
            content = format_swagger_to_markdown(spec, target_op, url)
            default_ext = ".md"

        slug = ""
        if target_op:
            clean_op = target_op['path'].strip('/').replace('/', '_')
            slug = f"{target_op['method'].lower()}_{clean_op}"
        else:
            slug = parsed_url.netloc.replace('.', '_') + (parsed_url.path.strip('/').replace('/', '_') or "_swagger")

    else:
        print(f"📄 [wtt] Processing web page content...")
        page_data = WebPageFetcher.fetch_page(url, session, force_js=force_js)

        slug = page_data['title'].lower()
        slug = re.sub(r'[^a-z0-9]+', '_', slug).strip('_')[:50] or "webpage"

        if fmt == "json":
            content = json.dumps(page_data, indent=2)
            default_ext = ".json"
        elif fmt == "txt":
            content = f"Title: {page_data['title']}\nURL: {page_data['url']}\n\n{page_data['clean_text']}"
            default_ext = ".txt"
        elif fmt == "html":
            content = page_data['html']
            default_ext = ".html"
        else: # md
            content = f"# {page_data['title']}\n\nURL: {page_data['url']}\n\n{page_data['markdown']}"
            default_ext = ".md"

    # Save logic
    if os.path.isdir(target_path) or not os.path.splitext(target_path)[1]:
        os.makedirs(target_path, exist_ok=True)
        filename = f"{slug}{default_ext}"
        final_file_path = os.path.join(target_path, filename)
    else:
        parent_dir = os.path.dirname(target_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        final_file_path = target_path

    with open(final_file_path, "w", encoding="utf-8") as f:
        f.write(content)

    file_size_kb = os.path.getsize(final_file_path) / 1024.0
    preview = content[:2000] + ("\n... [truncated]" if len(content) > 2000 else "")
    return os.path.abspath(final_file_path), preview, round(file_size_kb, 2)


def start_web_server(port=7860):
    class WttWebHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ["/", "/index.html"]:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                web_ui_path = os.path.join(os.path.dirname(__file__), "web_ui.html")
                if os.path.exists(web_ui_path):
                    with open(web_ui_path, "rb") as f:
                        self.wfile.write(f.read())
                else:
                    self.wfile.write(b"<h1>web_ui.html missing</h1>")
            else:
                self.send_error(404, "Not Found")

        def do_POST(self):
            if self.path == "/api/convert":
                content_length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_length)
                try:
                    data = json.loads(body_bytes.decode("utf-8"))
                    url = data.get("url")
                    fmt = data.get("format", "md")
                    target_path = data.get("path", ".")
                    force_js = data.get("force_js", False)

                    final_path, preview, size_kb = convert_url(url, fmt, target_path, force_js)

                    res_payload = json.dumps({
                        "success": True,
                        "file_path": final_path,
                        "preview": preview,
                        "size_kb": size_kb
                    })
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(res_payload.encode("utf-8"))
                except Exception as e:
                    res_payload = json.dumps({"success": False, "error": str(e)})
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(res_payload.encode("utf-8"))
            else:
                self.send_error(404, "Not Found")

        def log_message(self, format, *args):
            pass

    server_address = ("", port)
    try:
        httpd = socketserver.TCPServer(server_address, WttWebHandler)
    except OSError:
        port += 1
        httpd = socketserver.TCPServer(("", port), WttWebHandler)

    server_url = f"http://localhost:{port}"
    print(f"\n🌐 [wtt web] Web UI server running at: {server_url}")
    print("✨ Opening Web UI in your browser... (Press Ctrl+C to stop server)\n")

    try:
        webbrowser.open(server_url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down wtt Web Server...")
        httpd.server_close()
        sys.exit(0)


def parse_args():
    raw_args = sys.argv[1:]

    # Web UI mode
    if any(arg.lower() in ["web", "--web", "-w"] for arg in raw_args):
        start_web_server()
        sys.exit(0)

    if "--help" in raw_args or ("-h" in raw_args and not any(a.lower() in ["--html", "html"] for a in raw_args)):
        print("Usage: wtt <url> [format_flag: --json|--md|--txt|--html] [path] [--js]")
        print("Or run 'wtt web' to launch Web UI mode in browser.")
        print("Or run 'wtt' without arguments for interactive CLI mode.\n")
        print("Formats:")
        print("  --json, -j    Structured JSON representation")
        print("  --md,   -m    Markdown document (default)")
        print("  --txt,  -t    Plain text document")
        print("  --html, -h    Full HTML document (ideal for cloning sites/portfolios)")
        print("Flags:")
        print("  --js          Force Playwright Headless Chromium JS rendering")
        print("  web, --web    Launch local Web UI server")
        print("\nExamples:")
        print('  wtt web')
        print('  wtt "https://api.example.com/swagger-docs/"')
        print('  wtt "https://king-jethro-developer-portfolio-39bdp8.v2.appdeploy.ai" --html')
        sys.exit(0)

    if not raw_args:
        print("⚡ Welcome to wtt Interactive CLI")
        print("---------------------------------------------")
        try:
            url = input("🌐 Enter URL: ").strip()
            while not url:
                print("❌ URL cannot be empty.", file=sys.stderr)
                url = input("🌐 Enter URL: ").strip()

            fmt_input = input("🎨 Format (--md, --json, --txt, --html) [default: --md]: ").strip().lower()
            fmt = "md"
            if "json" in fmt_input or fmt_input == "-j":
                fmt = "json"
            elif "html" in fmt_input or fmt_input in ["-html", "html"]:
                fmt = "html"
            elif "txt" in fmt_input or fmt_input == "-t":
                fmt = "txt"

            cwd = os.getcwd()
            path_input = input(f"📂 Output path (hit Enter to use current dir [{cwd}]): ").strip()
            target_path = path_input if path_input else "."

            return url, fmt, target_path, False
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(0)

    url = None
    fmt = "md"
    target_path = "."
    force_js = False

    non_flag_args = []
    for arg in raw_args:
        lower_arg = arg.lower()
        if lower_arg in ["--json", "-j", "json"]:
            fmt = "json"
        elif lower_arg in ["--md", "-m", "md"]:
            fmt = "md"
        elif lower_arg in ["--txt", "-t", "txt"]:
            fmt = "txt"
        elif lower_arg in ["--html", "-html", "html"]:
            fmt = "html"
        elif lower_arg in ["--js", "js"]:
            force_js = True
        else:
            non_flag_args.append(arg)

    if non_flag_args:
        url = non_flag_args[0]
    if len(non_flag_args) > 1:
        target_path = non_flag_args[1]

    if not url:
        print("❌ Error: Missing URL argument.", file=sys.stderr)
        print("Usage: wtt <url> [format] [path]", file=sys.stderr)
        sys.exit(1)

    return url, fmt, target_path, force_js


def main():
    url, fmt, target_path, force_js = parse_args()
    final_path, preview, size_kb = convert_url(url, fmt, target_path, force_js)
    print(f"✅ [wtt] Successfully written ({size_kb:.2f} KB) -> {final_path}")


if __name__ == "__main__":
    main()
