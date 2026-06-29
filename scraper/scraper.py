"""
Spirits Price Scraper
Scrapes current prices from Provi and Twin B2B, then updates the Excel spreadsheet.
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PROVI_EMAIL    = os.environ["PROVI_EMAIL"]
PROVI_PASSWORD = os.environ["PROVI_PASSWORD"]
TWIN_EMAIL     = os.environ["TWIN_EMAIL"]
TWIN_PASSWORD  = os.environ["TWIN_PASSWORD"]


def make_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=opts)


def try_find(driver, selectors, by=By.CSS_SELECTOR, timeout=10):
    """Try multiple selectors, return first match."""
    for sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, sel))
            )
            return el
        except TimeoutException:
            continue
    return None


def parse_price(text):
    """Extract first dollar amount from a string."""
    if not text:
        return None
    match = re.search(r"\$?([\d,]+\.?\d*)", text.replace(",", ""))
    if match:
        val = float(match.group(1))
        # Sanity check — spirits prices should be between $1 and $5000
        if 1 < val < 5000:
            return val
    return None


# ---------------------------------------------------------------------------
# PROVI
# ---------------------------------------------------------------------------

def provi_login(driver):
    log.info("Navigating to Provi login...")
    driver.get("https://www.provi.com/login")
    time.sleep(3)
    log.info(f"Page title: {driver.title}")
    log.info(f"Page URL: {driver.current_url}")

    # Try many possible selectors for email field
    email_selectors = [
        "input[type='email']",
        "input[name='email']",
        "input[id='email']",
        "input[placeholder*='email' i]",
        "input[placeholder*='Email' i]",
        "input[autocomplete='email']",
        "input[autocomplete='username']",
        "input[type='text']",
    ]
    email_field = try_find(driver, email_selectors)

    if not email_field:
        # Log page source snippet for debugging
        log.error("Could not find email field. Page source snippet:")
        log.error(driver.page_source[:2000])
        raise Exception("Provi: email field not found")

    email_field.clear()
    email_field.send_keys(PROVI_EMAIL)
    time.sleep(0.5)

    # Password field
    pass_selectors = [
        "input[type='password']",
        "input[name='password']",
        "input[id='password']",
        "input[placeholder*='password' i]",
    ]
    pass_field = try_find(driver, pass_selectors)
    if not pass_field:
        raise Exception("Provi: password field not found")

    pass_field.clear()
    pass_field.send_keys(PROVI_PASSWORD)
    time.sleep(0.5)

    # Submit
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button[class*='login' i]",
        "button[class*='sign' i]",
    ]
    submit_btn = try_find(driver, submit_selectors, timeout=5)
    if submit_btn:
        submit_btn.click()
    else:
        pass_field.send_keys(Keys.RETURN)

    time.sleep(5)
    log.info(f"After login URL: {driver.current_url}")
    log.info("Provi login submitted.")


def provi_search_price(driver, product_name):
    """Search for a product on Provi and return the price."""
    try:
        # Try navigating to shop/search page
        driver.get(f"https://www.provi.com/shop?q={product_name.replace(' ', '+')}")
        time.sleep(3)

        # Try to find price elements
        price_selectors = [
            "[data-testid='product-price']",
            "[class*='price' i]",
            "[class*='Price']",
            ".product-price",
            "[data-price]",
            "span[class*='cost' i]",
        ]
        for sel in price_selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els[:3]:  # Check first 3 matches
                    price = parse_price(el.text)
                    if price:
                        log.info(f"Provi: '{product_name}' -> ${price}")
                        return price
            except Exception:
                continue

        log.warning(f"Provi: no price found for '{product_name}'")
        return None

    except Exception as e:
        log.error(f"Provi error for '{product_name}': {e}")
        return None


def scrape_provi(products):
    results = {}
    driver = make_driver()
    try:
        provi_login(driver)
        for name in products:
            results[name] = provi_search_price(driver, name)
            time.sleep(1.5)
    except Exception as e:
        log.error(f"Provi scraping failed: {e}")
    finally:
        driver.quit()
    return results


# ---------------------------------------------------------------------------
# TWIN B2B
# ---------------------------------------------------------------------------

def twin_login(driver):
    log.info("Navigating to Twin B2B login...")
    driver.get("https://www.twinb2b.com/login")
    time.sleep(3)
    log.info(f"Page title: {driver.title}")
    log.info(f"Page URL: {driver.current_url}")

    email_selectors = [
        "input[type='email']",
        "input[name='email']",
        "input[id='email']",
        "input[placeholder*='email' i]",
        "input[autocomplete='email']",
        "input[autocomplete='username']",
        "input[type='text']",
    ]
    email_field = try_find(driver, email_selectors)
    if not email_field:
        log.error("Could not find Twin email field. Page source snippet:")
        log.error(driver.page_source[:2000])
        raise Exception("Twin B2B: email field not found")

    email_field.clear()
    email_field.send_keys(TWIN_EMAIL)
    time.sleep(0.5)

    pass_selectors = [
        "input[type='password']",
        "input[name='password']",
        "input[id='password']",
        "input[placeholder*='password' i]",
    ]
    pass_field = try_find(driver, pass_selectors)
    if not pass_field:
        raise Exception("Twin B2B: password field not found")

    pass_field.clear()
    pass_field.send_keys(TWIN_PASSWORD)
    time.sleep(0.5)

    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button[class*='login' i]",
        "button[class*='sign' i]",
    ]
    submit_btn = try_find(driver, submit_selectors, timeout=5)
    if submit_btn:
        submit_btn.click()
    else:
        pass_field.send_keys(Keys.RETURN)

    time.sleep(5)
    log.info(f"After login URL: {driver.current_url}")
    log.info("Twin B2B login submitted.")


def twin_search_price(driver, product_name):
    """Search for a product on Twin B2B and return the price."""
    try:
        driver.get(f"https://www.twinb2b.com/search?q={product_name.replace(' ', '+')}")
        time.sleep(3)

        price_selectors = [
            "[class*='price' i]",
            "[class*='Price']",
            ".product-price",
            "[data-price]",
            "span[class*='cost' i]",
        ]
        for sel in price_selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els[:3]:
                    price = parse_price(el.text)
                    if price:
                        log.info(f"Twin B2B: '{product_name}' -> ${price}")
                        return price
            except Exception:
                continue

        log.warning(f"Twin B2B: no price found for '{product_name}'")
        return None

    except Exception as e:
        log.error(f"Twin B2B error for '{product_name}': {e}")
        return None


def scrape_twin(products):
    results = {}
    driver = make_driver()
    try:
        twin_login(driver)
        for name in products:
            results[name] = twin_search_price(driver, name)
            time.sleep(1.5)
    except Exception as e:
        log.error(f"Twin B2B scraping failed: {e}")
    finally:
        driver.quit()
    return results
