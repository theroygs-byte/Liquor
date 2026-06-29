"""
Spirits Price Scraper - Provi and Twin B2B
"""

import os
import time
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PROVI_EMAIL    = os.environ["PROVI_EMAIL"]
PROVI_PASSWORD = os.environ["PROVI_PASSWORD"]
TWIN_EMAIL     = os.environ["TWIN_EMAIL"]
TWIN_PASSWORD  = os.environ["TWIN_PASSWORD"]


def make_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-extensions")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def try_find(driver, selectors, timeout=10):
    for sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
            )
            return el
        except TimeoutException:
            continue
    return None


def try_click(driver, selectors, timeout=8):
    for sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
            )
            el.click()
            return el
        except TimeoutException:
            continue
    return None


def parse_price(text):
    if not text:
        return None
    clean = text.replace(",", "").replace(" ", "")
    match = re.search(r"\$?([\d]+\.[\d]{2})", clean)
    if match:
        val = float(match.group(1))
        if 1 < val < 5000:
            return val
    return None


def get_prices_from_page(driver):
    """Try multiple CSS selectors to find prices on a search results page."""
    price_selectors = [
        "[data-testid='product-price']",
        "[class*='ProductPrice']",
        "[class*='product-price']",
        "[class*='Price__']",
        "[class*='price__']",
        ".price",
        "[class*='cost']",
        "[data-price]",
        "span[class*='price']",
        "div[class*='price']",
        "p[class*='price']",
    ]
    for sel in price_selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els[:5]:
                text = el.text.strip()
                price = parse_price(text)
                if price:
                    return price
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# PROVI
# ---------------------------------------------------------------------------

def provi_login(driver):
    log.info("Logging into Provi...")
    driver.get("https://www.provi.com/login")
    time.sleep(4)
    log.info(f"Provi login page title: {driver.title} | URL: {driver.current_url}")

    # Try to find email input with many strategies
    email_field = try_find(driver, [
        "input[type='email']",
        "input[name='email']",
        "input[id='email']",
        "input[placeholder*='email' i]",
        "input[placeholder*='Email']",
        "input[autocomplete='email']",
        "input[autocomplete='username']",
        "input[type='text']:not([type='hidden'])",
    ], timeout=15)

    if not email_field:
        # Try waiting longer and checking if we're already logged in
        time.sleep(5)
        if "shop" in driver.current_url or "dashboard" in driver.current_url:
            log.info("Provi: already logged in!")
            return
        log.error(f"Provi: email field not found. URL={driver.current_url}")
        log.error(f"Page source (first 3000 chars): {driver.page_source[:3000]}")
        raise Exception("Provi: email field not found")

    email_field.click()
    time.sleep(0.3)
    email_field.clear()
    email_field.send_keys(PROVI_EMAIL)
    time.sleep(0.5)

    pass_field = try_find(driver, [
        "input[type='password']",
        "input[name='password']",
        "input[id='password']",
    ])
    if not pass_field:
        raise Exception("Provi: password field not found")

    pass_field.click()
    time.sleep(0.3)
    pass_field.clear()
    pass_field.send_keys(PROVI_PASSWORD)
    time.sleep(0.5)

    # Click submit
    submitted = try_click(driver, [
        "button[type='submit']",
        "button[class*='login' i]",
        "button[class*='Login']",
        "button[class*='submit' i]",
        "input[type='submit']",
    ])
    if not submitted:
        pass_field.send_keys(Keys.RETURN)

    time.sleep(6)
    log.info(f"Provi after login URL: {driver.current_url}")


def provi_get_price(driver, product_name):
    try:
        url = f"https://www.provi.com/shop?query={product_name.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(3)

        price = get_prices_from_page(driver)
        if price:
            log.info(f"Provi: '{product_name}' -> ${price}")
        else:
            log.warning(f"Provi: no price for '{product_name}'")
        return price
    except Exception as e:
        log.error(f"Provi search error '{product_name}': {e}")
        return None


def scrape_provi(products):
    results = {}
    driver = make_driver()
    try:
        provi_login(driver)
        for name in products:
            results[name] = provi_get_price(driver, name)
            time.sleep(1)
    except Exception as e:
        log.error(f"Provi scraping failed: {e}")
        # Return empty results so Twin B2B still runs
        for name in products:
            if name not in results:
                results[name] = None
    finally:
        driver.quit()
    return results


# ---------------------------------------------------------------------------
# TWIN B2B
# ---------------------------------------------------------------------------

def twin_login(driver):
    log.info("Logging into Twin B2B...")
    driver.get("https://www.twinb2b.com/login")
    time.sleep(4)
    log.info(f"Twin login page title: {driver.title} | URL: {driver.current_url}")

    email_field = try_find(driver, [
        "input[type='email']",
        "input[name='email']",
        "input[id='email']",
        "input[placeholder*='email' i]",
        "input[autocomplete='email']",
        "input[autocomplete='username']",
        "input[type='text']:not([type='hidden'])",
    ], timeout=15)

    if not email_field:
        if "twinb2b.com" in driver.current_url and "login" not in driver.current_url:
            log.info("Twin: already logged in!")
            return
        log.error(f"Twin: email not found. URL={driver.current_url}")
        log.error(driver.page_source[:3000])
        raise Exception("Twin B2B: email field not found")

    email_field.click()
    time.sleep(0.3)
    email_field.clear()
    email_field.send_keys(TWIN_EMAIL)
    time.sleep(0.5)

    pass_field = try_find(driver, [
        "input[type='password']",
        "input[name='password']",
        "input[id='password']",
    ])
    if not pass_field:
        raise Exception("Twin B2B: password field not found")

    pass_field.click()
    time.sleep(0.3)
    pass_field.clear()
    pass_field.send_keys(TWIN_PASSWORD)
    time.sleep(0.5)

    submitted = try_click(driver, [
        "button[type='submit']",
        "input[type='submit']",
        "button[class*='login' i]",
        "button[class*='sign' i]",
    ])
    if not submitted:
        pass_field.send_keys(Keys.RETURN)

    time.sleep(6)
    log.info(f"Twin after login URL: {driver.current_url}")


def twin_get_price(driver, product_name):
    try:
        # Try different search URL patterns for Twin B2B
        for url in [
            f"https://www.twinb2b.com/search?term={product_name.replace(' ', '+')}",
            f"https://www.twinb2b.com/search?q={product_name.replace(' ', '+')}",
            f"https://twinb2b.com/search?term={product_name.replace(' ', '+')}",
        ]:
            driver.get(url)
            time.sleep(3)
            price = get_prices_from_page(driver)
            if price:
                log.info(f"Twin B2B: '{product_name}' -> ${price} (url: {url})")
                return price

        log.warning(f"Twin B2B: no price for '{product_name}'")
        return None
    except Exception as e:
        log.error(f"Twin B2B search error '{product_name}': {e}")
        return None


def scrape_twin(products):
    results = {}
    driver = make_driver()
    try:
        twin_login(driver)
        # Test search URL on first product to find correct pattern
        if products:
            log.info(f"Testing Twin B2B search with: '{products[0]}'")
            log.info(f"Current URL after login: {driver.current_url}")
        for name in products:
            results[name] = twin_get_price(driver, name)
            time.sleep(1)
    except Exception as e:
        log.error(f"Twin B2B scraping failed: {e}")
        for name in products:
            if name not in results:
                results[name] = None
    finally:
        driver.quit()
    return results


# ---------------------------------------------------------------------------
# SCRAPE BOTH
# ---------------------------------------------------------------------------

def scrape_all(products):
    """Scrape both Provi and Twin B2B for every product."""
    log.info(f"Scraping Provi for {len(products)} products...")
    provi_results = scrape_provi(products)

    log.info(f"Scraping Twin B2B for {len(products)} products...")
    twin_results = scrape_twin(products)

    combined = {}
    for name in products:
        combined[name] = {
            "provi": provi_results.get(name),
            "twin":  twin_results.get(name),
        }
    return combined
