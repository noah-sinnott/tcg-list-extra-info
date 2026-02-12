"""
Async Playwright Browser Service
Manages a preloaded shared browser on a background event loop for concurrent page scraping.
"""
import asyncio
import threading
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


# Background loop + shared browser state
_bg_loop = None
_bg_thread = None
_playwright_obj = None
_shared_browser = None

BROWSER_ARGS = [
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-extensions",
    "--disable-infobars",
]

BLOCKED_EXTENSIONS = (
    '.png', '.jpg', '.jpeg', '.gif', '.svg',
    '.webp', '.ico', '.woff', '.woff2', '.ttf', '.eot',
)


# ---------------------------------------------------------------------------
# Browser lifecycle
# ---------------------------------------------------------------------------

async def _init_browser():
    """Start Playwright and launch a shared Chromium browser."""
    global _playwright_obj, _shared_browser
    _playwright_obj = await async_playwright().start()
    _shared_browser = await _playwright_obj.chromium.launch(
        headless=True,
        args=BROWSER_ARGS,
    )


def _browser_thread_target():
    """Entry-point for the daemon thread that hosts the async event loop."""
    global _bg_loop
    loop = asyncio.new_event_loop()
    _bg_loop = loop
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_init_browser())
    loop.run_forever()


def start_browser():
    """Spawn the background browser thread (call once at startup)."""
    global _bg_thread
    _bg_thread = threading.Thread(target=_browser_thread_target, daemon=True)
    _bg_thread.start()


def get_shared_browser():
    """Return the shared browser instance (may be None if not yet ready)."""
    return _shared_browser


def run_async(coro):
    """Schedule *coro* on the background loop and block until it completes."""
    if _bg_loop is None:
        raise RuntimeError("Background browser loop not initialised")
    return asyncio.run_coroutine_threadsafe(coro, _bg_loop).result()


# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------

async def _scrape_list(list_url, browser):
    """Scrape a single mytcgcollection list URL and return cards grouped by set."""
    page = None
    context = None
    try:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            java_script_enabled=True,
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        # Block heavy resources for speed
        async def _route_handler(route):
            if any(route.request.url.endswith(ext) for ext in BLOCKED_EXTENSIONS):
                await route.abort()
            else:
                await route.continue_()

        try:
            await page.route("**/*", _route_handler)
        except Exception:
            pass

        await page.goto(list_url, wait_until="domcontentloaded")
        try:
            await page.wait_for_selector("div[data-cardid]", timeout=5000)
        except Exception:
            content = await page.content()
            if not BeautifulSoup(content, "html.parser").select("div[data-cardid]"):
                return {}

        soup = BeautifulSoup(await page.content(), "html.parser")

        cards_by_set = {}
        for elem in soup.select("div[data-cardid]"):
            name = elem.get("data-name", "")
            number = elem.get("data-number", "")
            if not name or not number:
                continue

            set_el = elem.select_one("div.flex.justify-between.mb-4 p.text-gray-500")
            set_name = set_el.get_text(strip=True) if set_el else "Unknown"

            link = elem.select_one("a[href^='/card/']")
            url = link.get("href", "") if link else ""

            cards_by_set.setdefault(set_name, []).append({
                "name": name,
                "number": number,
                "url": url,
            })

        return cards_by_set
    finally:
        try:
            if page:
                await page.close()
            if context:
                await context.close()
        except Exception:
            pass


async def scrape_all_lists(sources, browser):
    """Scrape all *sources* concurrently using the given *browser*.

    Returns a list of ``(source_name, cards_by_set)`` tuples.
    """
    tasks = []
    for src in sources:
        name = src.get("name", "Unknown Source")
        tasks.append((name, asyncio.create_task(_scrape_list(src["url"], browser))))

    results = []
    for name, task in tasks:
        try:
            results.append((name, await task))
        except Exception as exc:
            print(f"  Error scraping {name}: {exc}")
            results.append((name, {}))
    return results
