#!/usr/bin/env python3
"""
wtt (Web To Text / URL To Text / Web To HTML)
Converts websites/URLs, JS-rendered SPAs, and Swagger/OpenAPI docs into JSON, Markdown, Plain Text, or HTML locally.
"""

from wtt_core.cli import parse_args
from wtt_core.formatter import convert_url

def main():
    url, fmt, target_path, force_js = parse_args()
    final_path, preview, size_kb = convert_url(url, fmt, target_path, force_js)
    print(f"✅ [wtt] Successfully written ({size_kb:.2f} KB) -> {final_path}")

if __name__ == "__main__":
    main()
