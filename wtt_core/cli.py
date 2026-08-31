import sys
import os

from .server import start_web_server

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

    # Interactive mode if no arguments provided
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
