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
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=opts)


def wait_for(driver, by, selector, timeout=15):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


def parse_price(text):
    """Extract first dollar amount from a string, e.g. '$34.99/bottle' -> 34.99"""
    if not text:
        return None
    match = re.search(r"\$?([\d,]+\.?\d*)", text.replace(",", ""))
    return float(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# PROVI
# ---------------------------------------------------------------------------

def provi_login(driver):
    log.info("Logging into Provi...")
    driver.get("https://www.provi.com/login")
    time.sleep(2)
    wait_for(driver, By.NAME, "email").send_keys(PROVI_EMAIL)
    driver.find_element(By.NAME, "password").send_keys(PROVI_PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(4)
    log.info("Provi login submitted.")


def provi_search_price(driver, product_name):
    """Search for a product on Provi and return the price."""
    try:
        driver.get("https://www.provi.com/shop")
        time.sleep(2)

        # Find and use the search box
        search_selectors = [
            "input[placeholder*='Search']",
            "input[type='search']",
            "input[name='q']",
            "[data-testid='search-input']",
        ]
        search_box = None
        for sel in search_selectors:
            try:
                search_box = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                break
            except TimeoutException:
                continue

        if not search_box:
            log.warning(f"Provi: could not find search box for '{product_name}'")
            return None

        search_box.clear()
        search_box.send_keys(product_name)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)

        # Try to grab first product price
        price_selectors = [
            "[data-testid='product-price']",
            ".product-price",
            "[class*='price']",
            "[class*='Price']",
        ]
        for sel in price_selectors:
            try:
                el = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                price = parse_price(el.text)
                if price:
                    log.info(f"Provi: '{product_name}' -> ${price}")
                    return price
            except TimeoutException:
                continue

        log.warning(f"Provi: no price found for '{product_name}'")
        return None

    except Exception as e:
        log.error(f"Provi error for '{product_name}': {e}")
        return None


def scrape_provi(products):
    """
    products: list of product name strings
    Returns dict: {product_name: price_or_None}
    """
    results = {}
    driver = make_driver()
    try:
        provi_login(driver)
        for name in products:
            results[name] = provi_search_price(driver, name)
            time.sleep(1.5)
    finally:
        driver.quit()
    return results


# ---------------------------------------------------------------------------
# TWIN B2B
# ---------------------------------------------------------------------------

def twin_login(driver):
    log.info("Logging into Twin B2B...")
    driver.get("https://www.twinb2b.com/login")
    time.sleep(2)

    email_selectors = ["input[name='email']", "input[type='email']", "#email"]
    for sel in email_selectors:
        try:
            driver.find_element(By.CSS_SELECTOR, sel).send_keys(TWIN_EMAIL)
            break
        except NoSuchElementException:
            continue

    pass_selectors = ["input[name='password']", "input[type='password']", "#password"]
    for sel in pass_selectors:
        try:
            driver.find_element(By.CSS_SELECTOR, sel).send_keys(TWIN_PASSWORD)
            break
        except NoSuchElementException:
            continue

    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(4)
    log.info("Twin B2B login submitted.")


def twin_search_price(driver, product_name):
    """Search for a product on Twin B2B and return the price."""
    try:
        driver.get("https://www.twinb2b.com")
        time.sleep(2)

        search_selectors = [
            "input[placeholder*='Search']",
            "input[type='search']",
            "input[name='q']",
            "#search",
        ]
        search_box = None
        for sel in search_selectors:
            try:
                search_box = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                break
            except TimeoutException:
                continue

        if not search_box:
            log.warning(f"Twin B2B: could not find search box for '{product_name}'")
            return None

        search_box.clear()
        search_box.send_keys(product_name)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)

        price_selectors = [
            "[class*='price']",
            "[class*='Price']",
            ".product-price",
            "[data-price]",
        ]
        for sel in price_selectors:
            try:
                el = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                price = parse_price(el.text)
                if price:
                    log.info(f"Twin B2B: '{product_name}' -> ${price}")
                    return price
            except TimeoutException:
                continue

        log.warning(f"Twin B2B: no price found for '{product_name}'")
        return None

    except Exception as e:
        log.error(f"Twin B2B error for '{product_name}': {e}")
        return None


def scrape_twin(products):
    """
    products: list of product name strings
    Returns dict: {product_name: price_or_None}
    """
    results = {}
    driver = make_driver()
    try:
        twin_login(driver)
        for name in products:
            results[name] = twin_search_price(driver, name)
            time.sleep(1.5)
    finally:
        driver.quit()
    return results
