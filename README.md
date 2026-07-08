# Authorized Web Mirror

A developer-friendly Python tool for creating an authorized static mirror of a website.

It opens pages with Playwright, waits for the browser to load resources, saves HTML/CSS/JS/images/fonts/assets, and rewrites local references so the mirrored site can be served locally.

> This project is intended for websites you own, maintain, are archiving for internal use, or have explicit permission to mirror. It does not bypass CAPTCHAs, paywalls, anti-bot systems, private APIs, or access controls.

---

## Features

- Browser-rendered capture using Playwright/Chromium.
- Downloads HTML, CSS, JavaScript, images, fonts, SVGs, JSON, media files and other loaded assets.
- Rewrites local references in:
  - HTML attributes: `src`, `href`, `srcset`, `poster`, `data`, etc.
  - CSS `url(...)` references.
  - CSS `@import` references.
  - Inline `style="..."` attributes.
  - `<style>...</style>` blocks.
- Optional external asset mirroring for CDNs, font providers and image hosts.
- Optional authenticated session support using Playwright `storage_state`.
- robots.txt support enabled by default.
- Clean modular architecture suitable for GitHub and future extensions.
- `--max-pages 0` support for unlimited internal page crawling.

---

## Quick Start

### 1. Create and activate a virtual environment

```powershell
python.exe -m venv .venv
.\.venv\Scripts\activate
```

### 2. Install dependencies

```powershell
python.exe -m pip install -r requirements.txt
python.exe -m playwright install chromium
```

Or install as a local package:

```powershell
python.exe -m pip install -e .
python.exe -m playwright install chromium
```

### 3. Mirror a website

Using the module directly:

```powershell
python.exe -m web_mirror https://example.com -o mirror --max-pages 50
```

If installed with `pip install -e .`, you can also use the CLI command:

```powershell
web-mirror https://example.com -o mirror --max-pages 50
```

---

## Common Commands

### Mirror with no internal page limit

```powershell
python.exe -m web_mirror https://example.com -o mirror --max-pages 0
```

### Mirror with no internal page limit and include external assets

```powershell
python.exe -m web_mirror https://example.com -o mirror --max-pages 0 --include-external --delay 1
```

### Run Chromium visibly while mirroring

Useful for debugging websites that rely heavily on JavaScript.

```powershell
python.exe -m web_mirror https://example.com -o mirror --headed
```

### Limit asset size

```powershell
python.exe -m web_mirror https://example.com -o mirror --max-asset-mb 25
```

### Use a longer timeout

```powershell
python.exe -m web_mirror https://example.com -o mirror --timeout-ms 90000
```

---

## Authenticated Sites You Own or Are Authorized to Access

Some sites require a valid session. You can open a real browser, sign in manually, and save the session state.

### Save session

```powershell
python.exe -m web_mirror https://your-site.com --save-auth auth.json
```

### Reuse session

```powershell
python.exe -m web_mirror https://your-site.com -o mirror --auth auth.json --max-pages 50
```

Keep `auth.json` private. Do not commit it to GitHub.

---

## Serve the Mirror Locally

After mirroring, serve the folder with Python:

```powershell
cd mirror
python.exe -m http.server 8080
```

Then open:

```text
http://localhost:8080
```

The generated structure usually looks like this:

```text
mirror/
└── example.com/
    ├── index.html
    ├── about/
    │   └── index.html
    ├── assets/
    │   ├── app.css
    │   ├── app.js
    │   └── logo.svg
    └── fonts/
        └── inter.woff2
```

---

## Architecture

```text
src/web_mirror/
├── __init__.py
├── __main__.py
├── browser.py       # Playwright lifecycle and auth-state helper
├── cli.py           # CLI argument parsing and config creation
├── config.py        # Immutable runtime configuration
├── crawler.py       # High-level crawl orchestration
├── policies.py      # URL scope and robots.txt policies
├── resources.py     # Network resource capture/fetch facade
├── rewriters.py     # HTML/CSS rewriting logic
├── storage.py       # URL-to-local-path mapping and file persistence
└── url_utils.py     # URL normalization helpers
```

### Design Patterns Used

#### 1. Orchestrator

`MirrorCrawler` coordinates the high-level process:

1. Open page.
2. Capture browser responses.
3. Rewrite rendered HTML.
4. Save page.
5. Queue internal links.

The crawler does not directly know how to rewrite CSS, map files, or evaluate robots.txt.

#### 2. Facade

`ResourceManager` hides the details of:

- Playwright network responses.
- Fallback asset downloads with `requests`.
- Asset size limits.
- robots.txt checks.
- CSS post-processing.

HTML and CSS rewriters only ask for: “ensure this asset exists locally.”

#### 3. Repository

`FileStore` owns all filesystem concerns:

- Safe filenames.
- Query hash handling.
- Extension inference from content type.
- URL-to-path mapping.
- Relative path generation.

#### 4. Policy Object

`ScopePolicy` centralizes decisions about what can be visited or saved.

Pages are intentionally limited to the starting domain. External resources are only saved when `--include-external` is enabled.

#### 5. Adapter

`RobotsPolicy` adapts Python’s `urllib.robotparser` API into a simple `can_fetch(url)` method.

#### 6. Context Manager

`BrowserSession` manages the Playwright lifecycle and guarantees cleanup of browser/context resources.

---

## CLI Reference

```text
usage: web-mirror [-h] [-o OUTPUT] [--max-pages MAX_PAGES]
                  [--include-external] [--no-robots] [--delay DELAY]
                  [--timeout-ms TIMEOUT_MS] [--max-asset-mb MAX_ASSET_MB]
                  [--auth AUTH] [--headed] [--save-auth SAVE_AUTH]
                  url
```

### Arguments

| Option | Description |
|---|---|
| `url` | Initial URL to mirror. |
| `-o`, `--output` | Output directory. Default: `mirror`. |
| `--max-pages` | Maximum internal pages to crawl. Use `0` for unlimited. |
| `--include-external` | Save external assets such as CDN scripts, fonts and images. |
| `--no-robots` | Disable robots.txt checks. Use only for sites you own/control. |
| `--delay` | Delay between page visits in seconds. Default: `0.5`. |
| `--timeout-ms` | Page load timeout in milliseconds. Default: `45000`. |
| `--max-asset-mb` | Maximum asset size in MB. Default: `80`. |
| `--auth` | Path to a saved Playwright auth-state JSON file. |
| `--headed` | Open Chromium visibly. Useful for debugging. |
| `--save-auth` | Save a manual login session to a JSON file. |

---

## Development

### Install dev dependencies

```powershell
python.exe -m pip install -e ".[dev]"
python.exe -m playwright install chromium
```

### Run linting

```powershell
ruff check src
```

### Run the CLI locally

```powershell
python.exe -m web_mirror https://example.com -o mirror --max-pages 5 --headed
```

---

## Limitations

A static mirror is not the same as the original backend.

This tool can save the files that the browser can access and rewrite many local references, but it cannot reproduce:

- Server-side rendering at request time.
- Databases.
- Private APIs.
- Payment flows.
- Forms that depend on a backend.
- WebSockets or live dashboards.
- Authentication systems.
- CAPTCHA/anti-bot flows.
- Paywalled or restricted content without permission.

For your own projects, the most reliable static output is usually the framework’s native export/build process, such as Astro, Vite, Next.js static export, Nuxt generate, etc. This mirror is useful when you do not have access to the original build pipeline or want an archival copy of rendered pages.

---

## Safe and Responsible Use

Use this tool only when you have permission to mirror the content. Respect site terms, rate limits, robots.txt, copyright, privacy and access controls.

Recommended defaults:

```powershell
python.exe -m web_mirror https://example.com -o mirror --delay 1 --max-pages 100
```

Use `--max-pages 0` carefully. On large websites it can create a very large local folder and run for a long time.

---

## Roadmap Ideas

- Add JSON crawl report.
- Add retry/backoff strategy.
- Add asset deduplication by content hash.
- Add sitemap.xml support.
- Add include/exclude URL patterns.
- Add tests for URL-to-path mapping and rewriters.
- Add Dockerfile.
- Add GitHub Actions workflow.

---

## License

MIT
