import sys
import os
import json
import http.server
import socketserver
import webbrowser

from .formatter import convert_url

def start_web_server(port=7860):
    """Launches local HTTP server serving web_ui.html and convert API endpoint."""

    class WttWebHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ["/", "/index.html"]:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                # Project root directory where web_ui.html resides
                root_dir = os.path.dirname(os.path.dirname(__file__))
                web_ui_path = os.path.join(root_dir, "web_ui.html")
                if os.path.exists(web_ui_path):
                    with open(web_ui_path, "rb") as f:
                        self.wfile.write(f.read())
                else:
                    self.wfile.write(b"<h1>web_ui.html missing</h1>")
            elif self.path.startswith("/fonts/"):
                root_dir = os.path.dirname(os.path.dirname(__file__))
                font_filename = os.path.basename(self.path)
                font_path = os.path.join(root_dir, "fonts", font_filename)
                if os.path.exists(font_path):
                    self.send_response(200)
                    self.send_header("Content-Type", "font/ttf")
                    self.end_headers()
                    with open(font_path, "rb") as f:
                        self.wfile.write(f.read())
                else:
                    self.send_error(404, "Font File Not Found")
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
