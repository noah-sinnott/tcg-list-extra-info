"""
Browser Pool Service (Playwright)
Manages thread-local Playwright browser instances for thread-safe operation
"""
import threading
from playwright.sync_api import sync_playwright


# Thread-local storage for browser instances
_thread_local = threading.local()


class BrowserManager:
    """Manages Playwright browser lifecycle for the current thread"""
    
    def __init__(self):
        self._playwright = None
        self._browser = None
    
    def _ensure_browser(self):
        """Ensure browser is initialized for this thread"""
        if self._browser is None:
            print(f"Initializing Playwright browser for thread {threading.current_thread().name}...")
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-infobars",
                ]
            )
        return self._browser
    
    def get_page(self, timeout=30):
        """
        Get a new page from a fresh context
        
        Args:
            timeout: Not used, kept for API compatibility
            
        Returns:
            tuple: (page, context)
        """
        browser = self._ensure_browser()
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            java_script_enabled=True,
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 720},
        )
        
        page = context.new_page()
        
        # Block images, fonts, and other non-essential resources for speed
        page.route("**/*.{png,jpg,jpeg,gif,svg,webp,ico,woff,woff2,ttf,eot}", lambda route: route.abort())
        
        print(f"Page created for thread {threading.current_thread().name}")
        return page, context
    
    def return_page(self, page, context):
        """
        Close a used page and context
        
        Args:
            page: The page instance to close
            context: The context instance to close
        """
        try:
            if page:
                page.close()
            if context:
                context.close()
                print("Context closed")
        except Exception as e:
            print(f"Error closing page/context: {e}")
    
    def shutdown(self):
        """Shutdown browser for this thread"""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            print(f"Browser shutdown for thread {threading.current_thread().name}")
        except Exception as e:
            print(f"Error during shutdown: {e}")


def _get_thread_browser_manager():
    """Get or create the BrowserManager for the current thread"""
    if not hasattr(_thread_local, 'browser_manager'):
        _thread_local.browser_manager = BrowserManager()
    return _thread_local.browser_manager


class BrowserPool:
    """Thread-safe browser pool using thread-local storage"""
    
    def __init__(self, pool_size=3):
        """
        Initialize the browser pool
        
        Args:
            pool_size: Not used, kept for API compatibility
        """
        print(f"Initializing thread-local Playwright browser pool...")
    
    def get_page(self, timeout=30):
        """Get a page from the current thread's browser"""
        manager = _get_thread_browser_manager()
        return manager.get_page(timeout)
    
    def return_page(self, page, context):
        """Return/close a page"""
        manager = _get_thread_browser_manager()
        manager.return_page(page, context)
    
    def shutdown(self):
        """Shutdown is handled per-thread"""
        print("Browser pool shutdown requested")


# Global pool instance
_browser_pool = None
_pool_lock = threading.Lock()


def get_pool(pool_size=3):
    """
    Get or create the global browser pool instance
    
    Args:
        pool_size: Number of contexts to maintain in the pool
        
    Returns:
        BrowserPool instance
    """
    global _browser_pool
    
    with _pool_lock:
        if _browser_pool is None:
            _browser_pool = BrowserPool(pool_size=pool_size)
        return _browser_pool

