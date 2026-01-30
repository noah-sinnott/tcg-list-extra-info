"""
WebDriver Pool Service
Manages a pool of pre-loaded WebDriver instances for improved performance
"""
import threading
from queue import Queue, Empty
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


class WebDriverPool:
    """Manages a pool of pre-loaded WebDriver instances"""
    
    def __init__(self, pool_size=3):
        """
        Initialize the WebDriver pool
        
        Args:
            pool_size: Number of WebDriver instances to maintain in the pool
        """
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        
        # Pre-load initial drivers
        print(f"Initializing WebDriver pool with {pool_size} instances...")
        for i in range(pool_size):
            driver = self._create_driver()
            if driver:
                self.pool.put(driver)
                print(f"  Driver {i+1}/{pool_size} loaded")
    
    def _create_driver(self):
        """Create a new WebDriver instance with standard options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except Exception as e:
            print(f"Error creating WebDriver: {e}")
            return None
    
    def get_driver(self, timeout=30):
        """
        Get a WebDriver from the pool and immediately create a replacement
        
        Args:
            timeout: Maximum time to wait for a driver (seconds)
            
        Returns:
            WebDriver instance or None if timeout
        """
        try:
            driver = self.pool.get(timeout=timeout)
            print(f"Driver acquired from pool (remaining: {self.pool.qsize()})")
            
            # Immediately create a new driver to replace the one we just took
            def create_replacement():
                new_driver = self._create_driver()
                if new_driver:
                    self.pool.put(new_driver)
                    print(f"Replacement driver added to pool (current size: {self.pool.qsize()})")
            
            # Create replacement in a separate thread so it doesn't block
            threading.Thread(target=create_replacement, daemon=True).start()
            
            return driver
        except Empty:
            print("Timeout waiting for available driver")
            return None
    
    def return_driver(self, driver):
        """
        Close a used driver
        
        Args:
            driver: The WebDriver instance to close
        """
        try:
            if driver:
                driver.quit()
                print(f"Driver closed")
        except Exception as e:
            print(f"Error closing driver: {e}")
    
    def shutdown(self):
        """Shutdown the pool and close all drivers"""
        print("Shutting down WebDriver pool...")
        
        # Close all drivers in the pool
        while not self.pool.empty():
            try:
                driver = self.pool.get_nowait()
                driver.quit()
            except Exception as e:
                print(f"Error closing driver during shutdown: {e}")
        
        print("WebDriver pool shutdown complete")


# Global pool instance
_driver_pool = None
_pool_lock = threading.Lock()


def get_pool(pool_size=3):
    """
    Get or create the global WebDriver pool instance
    
    Args:
        pool_size: Number of drivers to maintain in the pool
        
    Returns:
        WebDriverPool instance
    """
    global _driver_pool
    
    with _pool_lock:
        if _driver_pool is None:
            _driver_pool = WebDriverPool(pool_size=pool_size)
        return _driver_pool

