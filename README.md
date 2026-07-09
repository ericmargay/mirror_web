# Web Mirror Pro

A Python-based static website mirroring tool that uses Playwright to render pages like a real browser, capture loaded resources, and save a local static copy of a website.

This project is designed for authorized use cases such as backing up your own websites, archiving public pages you are allowed to access, testing static exports, or studying frontend structure.

> This tool is not intended to bypass captchas, paywalls, authentication systems, anti-bot protections, rate limits, or any access restrictions.

---

## Features

- Renders pages using Chromium through Playwright.
- Saves HTML pages as local files.
- Captures loaded assets from browser network responses.
- Downloads common frontend resources:
  - CSS
  - JavaScript
  - Images
  - SVG
  - Fonts
  - JSON
  - Videos/audio when discovered
  - Manifests and favicons
  - GLB/GLTF and other static files when loaded by the page
- Rewrites local HTML asset references.
- Rewrites CSS `url(...)` and `@import` references.
- Supports internal crawling.
- Supports optional external asset downloading.
- Supports `robots.txt` by default.
- Supports authorized browser sessions using Playwright storage state.
- Includes a direct `run.py` entrypoint so the project can be executed without installing it as a package.
- Can also be installed as a local editable Python package.

---

## Project Structure

```text
web-mirror-pro/
├── README.md
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── run.py
└── src/
    └── web_mirror/
        ├── __init__.py
        ├── __main__.py
        ├── browser.py
        ├── cli.py
        ├── config.py
        ├── crawler.py
        ├── policies.py
        ├── resources.py
        ├── rewriters.py
        ├── storage.py
        └── url_utils.py
```

---

## Requirements

- Python 3.10 or newer
- pip
- Playwright Chromium browser runtime

The project is intended to work on Windows, macOS, and Linux.

---

## Installation

Install the dependencies:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

If your system uses `python3` instead of `python`, use:

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

---

## Quick Start

From the project root, run:

```bash
python run.py https://example.com -o mirror_example --max-pages 50
```

If your system uses `python3`:

```bash
python3 run.py https://example.com -o mirror_example --max-pages 50
```

This will:

1. Open the website with Chromium.
2. Render the page.
3. Save the HTML.
4. Capture and save loaded assets.
5. Rewrite local references when possible.
6. Continue crawling internal links until the page limit is reached.

---

## Download External Assets

By default, the crawler saves resources from the same domain. To also save external assets from CDNs, font providers, image hosts, and other third-party sources, use:

```bash
python run.py https://example.com -o mirror_example --max-pages 50 --include-external
```

Example:

```bash
python run.py https://limbs.fromtheghost.com/ -o web_mirror_limbs_fromtheghost --max-pages 5000 --include-external
```

---

## Unlimited Internal Pages

Use `--max-pages 0` to remove the internal page limit:

```bash
python run.py https://example.com -o mirror_example --max-pages 0 --include-external
```

Be careful with this option. Large websites can contain thousands or millions of internal URLs.

Recommended safer version:

```bash
python run.py https://example.com -o mirror_example --max-pages 5000 --include-external --delay 1
```

---

## Run the Mirrored Site Locally

After the mirror is generated, you can serve the downloaded site with Python's built-in HTTP server.

For example, if you used:

```bash
python run.py https://example.com -o mirror_example --max-pages 50 --include-external
```

Enter the generated output folder:

```bash
cd mirror_example
```

Start a local server:

```bash
python -m http.server 8080
```

If your system uses `python3`:

```bash
python3 -m http.server 8080
```

Then open this in your browser:

```text
http://localhost:8080
```

Most mirrors are saved inside a domain folder. For example, if the mirrored site was `https://example.com`, the local files may be inside:

```text
mirror_example/example.com/
```

In that case, open:

```text
http://localhost:8080/example.com/
```

For the example:

```bash
python run.py https://limbs.fromtheghost.com/ -o web_mirror_limbs_fromtheghost --max-pages 5000 --include-external
```

Run:

```bash
cd web_mirror_limbs_fromtheghost
python -m http.server 8080
```

Then try:

```text
http://localhost:8080/limbs.fromtheghost.com/
```

If the domain folder name is slightly different because of filename sanitization, list the output directory and open the folder that was generated.

On Windows PowerShell:

```powershell
dir
```

On macOS/Linux:

```bash
ls
```

---

## Authorized Login Sessions

For websites you own or are allowed to access, you can manually log in through the browser and save the session.

Create an authorized session:

```bash
python run.py https://your-site.com --save-auth auth.json
```

A visible browser will open. Log in manually. When finished, return to the terminal and press `ENTER`.

Then reuse that session:

```bash
python run.py https://your-site.com -o mirror_private --auth auth.json --max-pages 100
```

`auth.json` may contain sensitive authentication cookies or tokens. Do not commit it to Git.

---

## CLI Reference

```text
python run.py URL [options]
```

### Arguments

| Argument | Description |
|---|---|
| `URL` | Initial URL to mirror. Example: `https://example.com` |

### Options

| Option | Description |
|---|---|
| `-o`, `--output` | Output folder. Default: `mirror` |
| `--max-pages` | Maximum number of internal HTML pages to crawl. Use `0` for unlimited. |
| `--include-external` | Save external assets loaded from third-party domains. |
| `--no-robots` | Disable `robots.txt` checking. Use responsibly. |
| `--delay` | Delay between page visits, in seconds. |
| `--timeout-ms` | Page navigation timeout in milliseconds. |
| `--max-asset-mb` | Maximum size per downloaded asset. |
| `--auth` | Path to a Playwright storage state file such as `auth.json`. |
| `--headed` | Run Chromium in visible mode. |
| `--save-auth` | Open browser and save a manual authenticated session. |

---

## Examples

### Mirror a small public site

```bash
python run.py https://example.com -o mirror_example --max-pages 20
```

### Mirror with external CDN assets

```bash
python run.py https://example.com -o mirror_example --max-pages 100 --include-external
```

### Large internal crawl

```bash
python run.py https://example.com -o mirror_example --max-pages 5000 --include-external --delay 1
```

### No page limit

```bash
python run.py https://example.com -o mirror_example --max-pages 0 --include-external --delay 1
```

### Run with a visible browser

```bash
python run.py https://example.com -o mirror_example --headed
```

### Use an authorized session

```bash
python run.py https://example.com --save-auth auth.json
python run.py https://example.com -o mirror_example --auth auth.json
```

---

## Optional Package Installation

The project can also be installed locally as a package:

```bash
python -m pip install -e .
```

Then you can run:

```bash
python -m web_mirror https://example.com -o mirror_example --max-pages 50
```

Or, if the console script is available:

```bash
web-mirror https://example.com -o mirror_example --max-pages 50
```

For the simplest workflow, `run.py` is recommended.

---

## Design and Architecture

The project separates responsibilities into small modules instead of keeping everything in one large script.

### Main Concepts

#### `config.py`

Defines the crawler configuration. This keeps command-line parsing separate from runtime behavior.

#### `cli.py`

Parses CLI arguments and creates the configuration object.

#### `crawler.py`

Coordinates the crawl process:

- Maintains the page queue.
- Opens pages with Playwright.
- Tracks visited pages.
- Sends HTML to the rewriting layer.
- Saves output through the storage layer.

#### `browser.py`

Creates and manages the Playwright browser context.

#### `resources.py`

Handles network responses and asset saving.

#### `rewriters.py`

Rewrites HTML and CSS references so local files point to local assets.

#### `storage.py`

Maps remote URLs to safe local file paths.

#### `policies.py`

Contains crawl policy decisions such as:

- Same-domain filtering
- External asset handling
- `robots.txt` checking

#### `url_utils.py`

Contains URL normalization and utility helpers.

---

## Patterns Used

### Separation of Concerns

Each module has a clear responsibility: crawling, storage, rewriting, resource handling, policy checks, and CLI setup are separated.

### Configuration Object

Runtime options are grouped into a single configuration object instead of being passed as many unrelated parameters.

### Strategy-Like Policy Layer

Crawling decisions are handled through policy functions/classes. This makes it easier to add new rules later.

Examples:

- Same-domain only
- Include external assets
- Respect or ignore `robots.txt`
- Maximum asset size

### Adapter Around Playwright

The browser handling is isolated from the crawler logic. This makes it easier to replace or extend the browser runtime in the future.

### Storage Abstraction

URL-to-file conversion is centralized, so filenames, query hashes, domain folders, and safe path generation are handled consistently.

---

## What This Tool Can Mirror Well

This tool works best with:

- Static websites
- Marketing pages
- Portfolio sites
- Documentation sites
- Landing pages
- Blogs
- Frontend-heavy pages where assets are loaded by the browser
- Sites where you have permission to archive the content

---

## Known Limitations

A static mirror is not the same as a full backend clone.

The following features may not work offline:

- Login flows
- Forms
- Search backed by a server
- Dashboards
- Payments
- API calls requiring a backend
- WebSockets
- Server-rendered dynamic content after interaction
- Infinite-scroll content not reached during the crawl
- Protected media streams
- Captcha-protected pages
- Paywalled or restricted pages
- Pages that require complex user interaction before loading all assets

For sites you own, the best result usually comes from combining this tool with a proper static export or production build from the original framework.

---

## Ethical and Legal Use

Use this project only when you have permission to access and archive the target website.

Good use cases:

- Backing up your own website
- Archiving public pages responsibly
- Testing static portability
- Studying frontend structure for educational purposes
- Saving authorized documentation
- Migrating your own frontend assets

Avoid using this tool for:

- Impersonation
- Phishing
- Credential harvesting
- Copyright infringement
- Bypassing access restrictions
- Evading anti-bot systems
- Circumventing paywalls
- Scraping private data without permission

---

## Recommended Workflow

For a GitHub project, a clean workflow could be:

```bash
git clone YOUR_REPO_URL
cd web-mirror-pro

python -m pip install -r requirements.txt
python -m playwright install chromium

python run.py https://example.com -o mirror_example --max-pages 100 --include-external
```

Then inspect the output:

```bash
cd mirror_example
python -m http.server 8080
```

Open:

```text
http://localhost:8080/example.com/
```

---

## Development

Install the project in editable mode if you want to work on it as a package:

```bash
python -m pip install -e .
```

Possible future development tools:

```bash
python -m pip install pytest ruff black mypy
```

---

## Roadmap

Potential improvements:

- Sitemap support
- Config file support using `mirror.yml`
- Better asset deduplication
- Better SPA route discovery
- Screenshot-based verification
- Export report as JSON
- Retry and backoff strategy
- Parallel asset downloads
- Media filtering by file type
- Include/exclude URL patterns
- Maximum crawl depth
- Custom headers
- Cookie import/export
- Dockerfile
- GitHub Actions CI
- Unit tests

---

## Troubleshooting

### `No module named web_mirror`

Use the direct runner:

```bash
python run.py https://example.com -o mirror_example
```

Or install the package locally:

```bash
python -m pip install -e .
```

Then run:

```bash
python -m web_mirror https://example.com -o mirror_example
```

### Playwright browser is missing

Run:

```bash
python -m playwright install chromium
```

### BeautifulSoup installation error

Do not install `BeautifulSoup`. That is an old package.

Install the correct package:

```bash
python -m pip install beautifulsoup4
```

The Python import remains:

```python
from bs4 import BeautifulSoup
```

### Output folder is too large

Reduce the page limit:

```bash
python run.py https://example.com -o mirror_example --max-pages 100
```

Or avoid external assets:

```bash
python run.py https://example.com -o mirror_example --max-pages 100
```

### The local copy does not look identical

Common causes:

- Some assets are blocked or loaded dynamically.
- The site depends on backend APIs.
- CSS or JS uses runtime-generated URLs.
- Fonts or media are loaded from third-party services.
- The page requires user interaction before loading all assets.

Try:

```bash
python run.py https://example.com -o mirror_example --max-pages 100 --include-external --headed
```

### Local server opens the wrong page

Start the server from inside the output directory:

```bash
cd mirror_example
python -m http.server 8080
```

Then open the generated domain folder:

```text
http://localhost:8080/example.com/
```

If you do not know the generated folder name, list the directory:

```bash
ls
```

On Windows PowerShell:

```powershell
dir
```

---

## License

Choose a license before publishing. Recommended options:

- MIT License for a permissive open-source project.
- Apache 2.0 if you want explicit patent language.
- No license if you do not want to grant reuse rights yet.

---

## Disclaimer

This project is provided for educational, archival, development, and authorized mirroring workflows. The user is responsible for complying with applicable laws, website terms, robots.txt, copyright restrictions, and access permissions.
