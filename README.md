# 🌐 wtt (Web To Text / Web To HTML)

**`wtt`** is a fast, intelligent CLI tool written in Python that converts websites, single-page applications (SPAs), developer portfolios, and Swagger/OpenAPI docs into clean **JSON**, **Markdown**, **Plain Text**, or **HTML** locally — without burning AI agent tokens or API credits!

---

## ⚡ Quick One-Line Installation

Install globally on Linux / macOS via `curl`:

```bash
curl -fsSL https://raw.githubusercontent.com/kingjethro999/wtt/main/install.sh | bash
```

---

## ✨ Features

- **⚡ OpenAPI / Swagger UI Auto-Discovery**: Automatically extracts raw JSON specs or formats documentation directly from JavaScript-rendered Swagger UI endpoints (such as Express, NestJS, and Fastify `swagger-ui-init.js`).
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

### 1. Swagger / OpenAPI Endpoint Extraction (JSON)

```bash
wtt "https://mc-backend-dev.wittytech.io/swagger-docs/#/Accounts/post_api_v1_accounts_activation_payment" --json /home/king/Documents/simulate
```

### 2. Swagger Root Spec Scraping

```bash
wtt "https://mc-backend-dev.wittytech.io/swagger-docs/" --json
```

### 3. Cloning a Portfolio / Website HTML Structure

```bash
wtt "https://king-jethro-developer-portfolio-39bdp8.v2.appdeploy.ai" --html
```

### 4. Scraping JS-Heavy Single Page Applications (SPAs)

```bash
wtt "https://d-a-r-k.vercel.app/" --html
```

### 5. Plain Text / Markdown Extraction

```bash
wtt "https://example.com" --md ./output_dir
wtt "https://example.com" --txt
```

---

## 🛠️ CLI Options

| Flag / Option | Description |
| --- | --- |
| `<url>` | Target website or Swagger UI URL (Required) |
| `--json`, `-j` | Output as structured JSON |
| `--md`, `-m` | Output as Markdown document (Default) |
| `--txt`, `-t` | Output as Plain Text document |
| `--html`, `-h` | Output as Prettified HTML document |
| `--js` | Force Playwright Headless Chromium JS rendering |
| `[path]` | Output directory or file path (Defaults to `.`) |

---

## 📄 License

MIT License © 2026 King Jethro
