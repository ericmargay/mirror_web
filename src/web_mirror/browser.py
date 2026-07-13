from __future__ import annotations

from pathlib import Path
from typing import Callable

from playwright.sync_api import Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from .snapshot import AUTO_SCROLL_JS, EXTRACT_JS


class BrowserSession:
    """Small wrapper around Playwright lifecycle."""

    def __init__(
        self,
        headed: bool,
        timeout_ms: int,
        auth_state: str | None,
        user_agent: str,
        on_response: Callable | None = None,
    ) -> None:
        self.headed = headed
        self.timeout_ms = timeout_ms
        self.auth_state = auth_state
        self.user_agent = user_agent
        self.on_response = on_response
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self) -> "BrowserSession":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=not self.headed)

        context_options = {
            "viewport": {"width": 1440, "height": 1200},
            "user_agent": self.user_agent,
        }
        if self.auth_state:
            context_options["storage_state"] = self.auth_state

        self._context = self._browser.new_context(**context_options)
        if self.on_response:
            self._context.on("response", self.on_response)

        self.page = self._context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def goto_and_get_content(self, url: str) -> str | None:
        if not self.page:
            raise RuntimeError("BrowserSession must be used as a context manager.")
        try:
            self.page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
        except PlaywrightTimeoutError:
            print("[warning] networkidle timeout; saving content loaded so far.")
        except Exception as exc:
            print(f"[error] page failed: {url} ({exc})")
            return None
        self.auto_scroll()
        return self.page.content()

    def auto_scroll(self) -> None:
        """Scroll to the bottom (and back) so lazy-loaded assets actually load."""

        if not self.page:
            return
        try:
            self.page.evaluate(AUTO_SCROLL_JS)
            self.page.wait_for_timeout(800)
        except Exception:
            pass  # scrolling is best-effort

    def extract_structured(self) -> dict | None:
        """Collect the structured snapshot of the current page (see snapshot.py)."""

        if not self.page:
            return None
        try:
            return self.page.evaluate(EXTRACT_JS)
        except Exception as exc:
            print(f"[warning] structured extraction failed: {exc}")
            return None


def save_auth_state(url: str, auth_file: str) -> None:
    """Open a visible browser so the user can sign in manually and save storage state."""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until="load", timeout=60_000)

        print("A browser window is open.")
        print("Sign in manually only if you are authorized to access this website.")
        input("Press ENTER here after you finish signing in... ")

        Path(auth_file).parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=auth_file)
        print(f"Auth state saved: {auth_file}")

        context.close()
        browser.close()
