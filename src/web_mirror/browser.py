from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from .config import MirrorConfig


class BrowserSession:
    """Thin wrapper around Playwright lifecycle.

    Pattern: Context Manager. Browser cleanup stays deterministic even if the crawl
    fails in the middle.
    """

    def __init__(self, config: MirrorConfig) -> None:
        self.config = config
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self) -> BrowserSession:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=not self.config.headed)

        context_options = {
            "viewport": {"width": 1440, "height": 1200},
            "user_agent": self.config.user_agent,
        }

        if self.config.auth_state:
            context_options["storage_state"] = str(self.config.auth_state)

        self.context = self.browser.new_context(**context_options)
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # noqa: ANN001
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def on_response(self, callback) -> None:  # noqa: ANN001
        if not self.context:
            raise RuntimeError("Browser context is not started.")
        self.context.on("response", callback)

    def goto_and_get_html(self, url: str) -> str:
        if not self.page:
            raise RuntimeError("Browser page is not started.")

        self.page.goto(url, wait_until="networkidle", timeout=self.config.timeout_ms)
        return self.page.content()


def save_auth_state(url: str, auth_file: Path) -> None:
    """Open a visible browser so the user can sign in manually and store cookies/session."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("A browser window will open.")
        print("Sign in only to sites where you are authorized to access the content.")
        print("When done, return here and press ENTER.")

        page.goto(url, wait_until="load", timeout=60_000)
        input("Press ENTER after signing in... ")

        context.storage_state(path=str(auth_file))
        print(f"Auth state saved to: {auth_file}")

        context.close()
        browser.close()
