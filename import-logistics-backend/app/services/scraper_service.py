# app/services/scraper_service.py
import asyncio
import logging
import re
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings

logger = logging.getLogger(__name__)

# Sources that require JS rendering — use Playwright
_PLAYWRIGHT_SOURCES = {"mobile_de", "autoscout24"}


class ScraperService:
    """
    Scrapes market prices from external sites.
    Uses httpx + BeautifulSoup for static sites.
    Falls back to Playwright for JS-rendered sites.
    SessionLocal is NOT created here — callers pass item data directly.
    """

    async def scrape_prices(
        self, item_name: str, category: str, source: str
    ) -> list[dict[str, Any]]:
        if not settings.SCRAPING_ENABLED:
            return []

        try:
            if source in _PLAYWRIGHT_SOURCES:
                return await self._scrape_with_playwright(item_name, category, source)
            return await self._scrape_with_httpx(item_name, category, source)
        except Exception as e:
            logger.error("Scraping failed for source=%s item=%r: %s", source, item_name, e)
            return []

    # ------------------------------------------------------------------
    # httpx scraper (static HTML)
    # ------------------------------------------------------------------
    async def _scrape_with_httpx(
        self, item_name: str, category: str, source: str
    ) -> list[dict[str, Any]]:
        url, currency, css_class = _SOURCE_CONFIG.get(source, (None, "USD", None))
        if not url:
            logger.warning("Unknown scraper source: %s", source)
            return []

        search_term = f"{item_name} {category}".replace(" ", "+")
        search_url  = f"{url}/search?query={search_term}"

        try:
            async with httpx.AsyncClient(
                timeout=15,
                headers={"User-Agent": settings.SCRAPING_USER_AGENT},
                follow_redirects=True,
            ) as client:
                resp = await client.get(search_url)
                resp.raise_for_status()

            soup    = BeautifulSoup(resp.content, "html.parser")
            results = self._parse_prices(soup, css_class, currency, search_url)

            await asyncio.sleep(1.5)   # polite delay
            return results

        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %d from %s: %s", e.response.status_code, source, e)
            return []

    def _parse_prices(
        self,
        soup: BeautifulSoup,
        css_class: Optional[str],
        currency: str,
        url: str,
    ) -> list[dict[str, Any]]:
        results = []
        if not css_class:
            return results

        elements = soup.find_all("span", class_=css_class)[:5]
        for el in elements:
            price = self._extract_price(el.get_text())
            if price:
                results.append({
                    "price":      price,
                    "currency":   currency,
                    "url":        url,
                    "confidence": 0.75,
                })
        return results

    # ------------------------------------------------------------------
    # Playwright scraper (JS-rendered sites)
    # ------------------------------------------------------------------
    async def _scrape_with_playwright(
        self, item_name: str, category: str, source: str
    ) -> list[dict[str, Any]]:
        try:
            from playwright.async_api import async_playwright

            search_term = f"{item_name} {category}"
            url, currency, _ = _SOURCE_CONFIG.get(source, (None, "EUR", None))
            if not url:
                return []

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page    = await browser.new_page(
                    user_agent=settings.SCRAPING_USER_AGENT
                )
                await page.goto(
                    f"{url}/search?query={search_term.replace(' ', '+')}",
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
                # Generic price extraction — works across most listing pages
                price_els = await page.query_selector_all("[class*='price']")
                results   = []
                for el in price_els[:5]:
                    text  = await el.text_content()
                    price = self._extract_price(text or "")
                    if price:
                        results.append({
                            "price":      price,
                            "currency":   currency,
                            "url":        page.url,
                            "confidence": 0.65,
                        })
                await browser.close()
                return results

        except Exception as e:
            logger.error("Playwright scrape failed for %s: %s", source, e)
            return []

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_price(text: str) -> Optional[float]:
        cleaned = text.replace(",", "").replace(" ", "")
        match   = re.search(r"\d+\.?\d*", cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        return None


# Source config: (base_url, currency, price_css_class)
_SOURCE_CONFIG: dict[str, tuple[str, str, Optional[str]]] = {
    "jiji":       ("https://jiji.ng",           "NGN", "price"),
    "ebay":       ("https://www.ebay.com/sch",   "USD", "s-item__price"),
    "mobile_de":  ("https://www.mobile.de",      "EUR", None),   # Playwright
    "autoscout24": ("https://www.autoscout24.com", "EUR", None),  # Playwright
    "bazos_cz":   ("https://www.bazos.cz",       "CZK", "price"),
}