"""Browser Controller via Playwright.

Provides programmatic browser control for web automation:
- navigate, click, type_text, extract_text, screenshot
- Risk tier 3 for read operations, tier 4 for form submissions and clicks.

Requires: pip install playwright && playwright install chromium
"""

from __future__ import annotations

import time
from typing import Optional

from infrastructure.os_control.risk_tier import RiskTier
from infrastructure.os_control.schemas import (
    BrowserAction,
    BrowserActionType,
    BrowserResult,
)
from utils.log import log_debug, log_error, log_info, log_warning


class BrowserController:
    """Playwright-based browser controller.

    Manages a single browser instance with one active page.
    All actions are synchronous wrappers around Playwright's sync API.
    """

    def __init__(self) -> None:
        self._browser = None
        self._page = None
        self._playwright = None
        self._initialized = False

    def _ensure_browser(self) -> None:
        """Lazily initialize the browser on first use."""
        if self._initialized and self._page:
            return

        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            self._page = self._browser.new_page()
            self._initialized = True
            log_info("[Browser] Chromium launched (headless)")
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )
        except Exception as e:
            log_error(f"[Browser] Failed to launch: {e}")
            raise RuntimeError(f"Browser launch failed: {e}")

    def execute(self, action: BrowserAction) -> BrowserResult:
        """Execute a browser action.

        Args:
            action: BrowserAction describing what to do.

        Returns:
            BrowserResult with outcome.
        """
        start_time = time.time()

        try:
            self._ensure_browser()
            assert self._page is not None

            handler = {
                BrowserActionType.NAVIGATE: self._navigate,
                BrowserActionType.CLICK: self._click,
                BrowserActionType.TYPE_TEXT: self._type_text,
                BrowserActionType.EXTRACT_TEXT: self._extract_text,
                BrowserActionType.SCREENSHOT: self._screenshot,
                BrowserActionType.SCROLL: self._scroll,
                BrowserActionType.WAIT: self._wait,
                BrowserActionType.EVALUATE: self._evaluate,
            }.get(action.action)

            if handler is None:
                return BrowserResult(
                    action=action.action,
                    success=False,
                    error=f"Unknown action: {action.action}",
                    execution_time_ms=0,
                    risk_tier=action.risk_tier,
                )

            result = handler(action)
            execution_time_ms = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time_ms
            return result

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            log_error(f"[Browser] Action {action.action} failed: {e}")
            return BrowserResult(
                action=action.action,
                success=False,
                error=str(e),
                execution_time_ms=execution_time_ms,
                risk_tier=action.risk_tier,
            )

    def _navigate(self, action: BrowserAction) -> BrowserResult:
        if not action.url:
            return BrowserResult(
                action=action.action, success=False,
                error="URL required for navigate", risk_tier=action.risk_tier,
            )
        log_info(f"[Browser] Navigating to: {action.url}")
        self._page.goto(action.url, timeout=action.timeout_seconds * 1000)
        return BrowserResult(
            action=action.action, success=True,
            url=self._page.url, title=self._page.title(),
            risk_tier=action.risk_tier,
        )

    def _click(self, action: BrowserAction) -> BrowserResult:
        if not action.selector:
            return BrowserResult(
                action=action.action, success=False,
                error="Selector required for click", risk_tier=action.risk_tier,
            )
        log_info(f"[Browser] Clicking: {action.selector}")
        self._page.click(action.selector, timeout=action.timeout_seconds * 1000)
        return BrowserResult(
            action=action.action, success=True,
            url=self._page.url, title=self._page.title(),
            risk_tier=action.risk_tier,
        )

    def _type_text(self, action: BrowserAction) -> BrowserResult:
        if not action.selector or not action.text:
            return BrowserResult(
                action=action.action, success=False,
                error="Selector and text required for type_text",
                risk_tier=action.risk_tier,
            )
        log_info(f"[Browser] Typing into: {action.selector}")
        self._page.fill(action.selector, action.text, timeout=action.timeout_seconds * 1000)
        return BrowserResult(
            action=action.action, success=True,
            url=self._page.url, risk_tier=action.risk_tier,
        )

    def _extract_text(self, action: BrowserAction) -> BrowserResult:
        selector = action.selector or "body"
        log_info(f"[Browser] Extracting text from: {selector}")
        text = self._page.inner_text(selector, timeout=action.timeout_seconds * 1000)
        # Truncate large extractions
        if len(text) > 10_000:
            text = text[:10_000] + "\n... (truncated)"
        return BrowserResult(
            action=action.action, success=True,
            content=text, url=self._page.url,
            risk_tier=action.risk_tier,
        )

    def _screenshot(self, action: BrowserAction) -> BrowserResult:
        import tempfile
        path = tempfile.mktemp(suffix=".png")
        log_info(f"[Browser] Screenshot → {path}")
        self._page.screenshot(path=path, full_page=True)
        return BrowserResult(
            action=action.action, success=True,
            content=path, url=self._page.url,
            risk_tier=action.risk_tier,
        )

    def _scroll(self, action: BrowserAction) -> BrowserResult:
        direction = action.text or "down"
        pixels = 500
        if direction == "down":
            self._page.evaluate(f"window.scrollBy(0, {pixels})")
        elif direction == "up":
            self._page.evaluate(f"window.scrollBy(0, -{pixels})")
        return BrowserResult(
            action=action.action, success=True,
            url=self._page.url, risk_tier=action.risk_tier,
        )

    def _wait(self, action: BrowserAction) -> BrowserResult:
        if action.selector:
            self._page.wait_for_selector(
                action.selector,
                timeout=action.timeout_seconds * 1000,
            )
        else:
            self._page.wait_for_timeout(action.timeout_seconds * 1000)
        return BrowserResult(
            action=action.action, success=True,
            url=self._page.url, risk_tier=action.risk_tier,
        )

    def _evaluate(self, action: BrowserAction) -> BrowserResult:
        if not action.text:
            return BrowserResult(
                action=action.action, success=False,
                error="JavaScript expression required for evaluate",
                risk_tier=action.risk_tier,
            )
        log_info(f"[Browser] Evaluating JS: {action.text[:80]}")
        result = self._page.evaluate(action.text)
        return BrowserResult(
            action=action.action, success=True,
            content=str(result)[:5000], url=self._page.url,
            risk_tier=action.risk_tier,
        )

    def close(self) -> None:
        """Close the browser and clean up."""
        try:
            if self._page:
                self._page.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            self._initialized = False
            log_info("[Browser] Closed")
        except Exception as e:
            log_warning(f"[Browser] Cleanup error: {e}")
        finally:
            self._page = None
            self._browser = None
            self._playwright = None
