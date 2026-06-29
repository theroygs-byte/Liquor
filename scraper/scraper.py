"""
Spirits Price Scraper
Scrapes prices from BOTH Provi and Twin B2B for every product.
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
    if not text:
        return None
    match = re.search(r"\$?([\d,]+\.?\d*)", text.replace(",", ""))
    if match:
        val = float(match.group(1))
        if 1 < val < 5000:
            return val
    return None


# ---------------------------------------------------------------------------
# PROVI
# ---------------------------------------------------------------------------

def provi_login(driver):
    log.info("Logging into Provi...")
    driver.get("https://www.provi.com/login")
    time.sleep(3)

    email_field = try_find(driver, [
        "input[type='email']", "input[name='email']", "input[id='email']",
        "input[placeholder*='email' i]", "input[autocomplete='email']",
        "input[autocomplete='username']", "input[type='text']",
    ])
    if not email_field:
        log.error(driver.page_source[:2000])
        raise Exception("Provi: email field not found")

    email_field.clear()
    email_field.send_keys(PROVI_EMAIL)
    time.sleep(0.5)

    pass_field = try_find(driver, [
        "input[type='password']", "input[name='password']",
        "input[id='password']", "input[placeholder*='password' i]",
    ])
    if not pass_field:
        raise Exception("Provi: password field not found")

    pass_field.clear()
    pass_field.send_keys(PROVI_PASSWORD)
    time.sleep(0.5)

    submit_btn = try_find(driver, [
        "button[type='submit']", "input[type='submit']",
        "button[class*='login' i]", "button[class*='sign' i]",
    ], timeout=5)
    if submit_btn:
        submit_btn.click()
    else:
        pass_field.send_keys(Keys.RETURN)

    time.sleep(5)
    log.info(f"Provi login done. URL: {driver.current_url}")


def provi_get_price(driver, product_name):
    try:
        driver.get(f"https://www.provi.com/shop?q={product_name.replace(' ', '+')}")
        time.sleep(3)
        for sel in ["[data-testid='product-price']", "[class*='price' i]",
                    "[class*='Price']", ".product-price", "[data-price]"]:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els[:3]:
                    price = parse_price(el.text)
                    if price:
                        log.info(f"Provi: '{product_name}' -> ${price}")
                        return price
            except Exception:
                continue
        log.warning(f"Provi: no price for '{product_name}'")
        return None
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
    log.info("Logging into Twin B2B...")
    driver.get("https://www.twinb2b.com/login")
    time.sleep(3)

    email_field = try_find(driver, [
        "input[type='email']", "input[name='email']", "input[id='email']",
        "input[placeholder*='email' i]", "input[autocomplete='email']",
        "input[autocomplete='username']", "input[type='text']",
    ])
    if not email_field:
        log.error(driver.page_source[:2000])
        raise Exception("Twin B2B: email field not found")

    email_field.clear()
    email_field.send_keys(TWIN_EMAIL)
    time.sleep(0.5)

    pass_field = try_find(driver, [
        "input[type='password']", "input[name='password']",
        "input[id='password']", "input[placeholder*='password' i]",
    ])
    if not pass_field:
        raise Exception("Twin B2B: password field not found")

    pass_field.clear()
    pass_field.send_keys(TWIN_PASSWORD)
    time.sleep(0.5)

    submit_btn = try_find(driver, [
        "button[type='submit']", "input[type='submit']",
        "button[class*='login' i]", "button[class*='sign' i]",
    ], timeout=5)
    if submit_btn:
        submit_btn.click()
    else:
        pass_field.send_keys(Keys.RETURN)

    time.sleep(5)
    log.info(f"Twin login done. URL: {driver.current_url}")


def twin_get_price(driver, product_name):
    try:
        driver.get(f"https://www.twinb2b.com/search?q={product_name.replace(' ', '+')}")
        time.sleep(3)
        for sel in ["[class*='price' i]", "[class*='Price']",
                    ".product-price", "[data-price]", "span[class*='cost' i]"]:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els[:3]:
                    price = parse_price(el.text)
                    if price:
                        log.info(f"Twin B2B: '{product_name}' -> ${price}")
                        return price
            except Exception:
                continue
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
        for name in products:
            results[name] = twin_get_price(driver, name)
            time.sleep(1.5)
    except Exception as e:
        log.error(f"Twin B2B scraping failed: {e}")
    finally:
        driver.quit()
    return results


# ---------------------------------------------------------------------------
# SCRAPE BOTH for ALL products
# ---------------------------------------------------------------------------

def scrape_all(products):
    """
    Scrape both Provi and Twin B2B for every product.
    Returns: {product_name: {"provi": price_or_None, "twin": price_or_None}}
    """
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
