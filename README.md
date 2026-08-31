# 🌐 wtt (Web To Text & HTML Converter)

**`wtt`** is a fast, intelligent CLI tool and local Web UI written in Python that converts websites, single-page applications (SPAs), developer portfolios, and Swagger/OpenAPI docs into clean **JSON**, **Markdown**, **Plain Text**, or **HTML** locally — without burning AI agent tokens or API credits!

---

## ⚡ Quick One-Line Installation

Install globally on Linux / macOS via `curl`:

```bash
curl -fsSL https://raw.githubusercontent.com/kingjethro999/wtt/main/install.sh | bash
```

---

## ✨ Features

- **🌐 Interactive Web UI (`wtt web`)**: Opens a modern local Web interface in your browser to paste links, choose format types, configure output paths, and track conversion progress visually.
- **⚡ OpenAPI / Swagger UI Auto-Discovery**: Automatically extracts raw JSON specs or formats documentation directly from JavaScript-rendered Swagger UI endpoints.
- **🎯 Hash Fragment Endpoint Extraction**: Directly isolates specific API paths & parameters when given URLs with fragments (e.g. `#/Accounts/post_api_v1_accounts_activation_payment`).
- **🎭 Headless JS / SPA Rendering**: Integrated with Playwright Headless Chromium to automatically render client-side SPAs (React, Next.js, Vue, portfolios).
- **🎨 Multi-Format Support**:
  - `--json`: Structured JSON schema & extracted data.
  - `--md`: Clean Markdown document (Default).
  - `--txt`: Stripped plain text content.
  - `--html`: Prettified HTML structure (ideal for cloning portfolio designs & site structure).
- **📂 Flexible Output Paths**: Save output directly into any directory or file path, defaulting to your current working directory.

---

## 🚀 Usage & Examples

### 1. Launch Interactive Web UI Mode
Launch a local Web UI server on `http://localhost:7860`:
```bash
wtt web
```

### 2. Interactive CLI Mode (No Arguments)
Simply type `wtt` in your terminal to launch the interactive setup wizard:
```bash
wtt
```

---

### One-Shot CLI Commands

#### 1. Swagger / OpenAPI Endpoint Extraction (JSON)
```bash
wtt "https://api.example.com/swagger-docs/#/Accounts/post_api_v1_accounts_activation_payment" --json /home/king/Documents/simulate
```

#### 2. Swagger Root Spec Scraping
```bash
wtt "https://api.example.com/swagger-docs/" --json
```

#### 3. Cloning a Portfolio / Website HTML Structure
```bash
wtt "https://king-jethro-developer-portfolio-39bdp8.v2.appdeploy.ai" --html
```

#### 4. Scraping JS-Heavy Single Page Applications (SPAs)
```bash
wtt "https://d-a-r-k.vercel.app/" --html
```

---

## 🛠️ CLI Options

| Flag / Option | Description |
| --- | --- |
| `web`, `--web` | Launch local Web UI server (`http://localhost:7860`) |
| `<url>` | Target website or Swagger UI URL |
| `--json`, `-j` | Output as structured JSON |
| `--md`, `-m` | Output as Markdown document (Default) |
| `--txt`, `-t` | Output as Plain Text document |
| `--html`, `-h` | Output as Prettified HTML document |
| `--js` | Force Playwright Headless Chromium JS rendering |
| `[path]` | Output directory or file path (Defaults to `.`) |

---

## 📄 License

MIT License © 2026 King Jethro
