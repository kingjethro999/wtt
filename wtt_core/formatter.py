import os
import re
import json
from urllib.parse import urlparse
import requests

from .openapi import OpenAPIParser
from .web import WebPageFetcher

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
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
