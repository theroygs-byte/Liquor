"""
Main entry point for Roy G's Spirits Price Tracker.
Scrapes BOTH Provi and Twin B2B for every product and writes comparison to Excel.
"""

import argparse
import logging
import sys
import os
from openpyxl import load_workbook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scraper"))

from scraper import scrape_all
from excel_updater import update_excel, DATA_START_ROW, MASTER_SHEET
from excel_updater import LEFT_ITEM_COL, RIGHT_ITEM_COL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def extract_all_products(filepath):
    wb = load_workbook(filepath, read_only=True)
    ws = wb[MASTER_SHEET]

    skip_values = {
        "vodka", "rum", "whiskey", "gin", "wine", "cordials",
        "beer/seltzer/rtd", "n/a bev", "garnish", "agave/tequila",
        "liquor\nlevel", "liquor level", "size", "par", "on hand",
        "need to order", "cost per bottle", "extended value", "vendor",
        "roy g's liquor inventory", "date:", "provi price", "twin price",
        "best price", "best vendor",
    }

    products = []
    for row in ws.iter_rows(min_row=DATA_START_ROW, values_only=True):
        for col_idx in [LEFT_ITEM_COL - 1, RIGHT_ITEM_COL - 1]:
            name = row[col_idx] if col_idx < len(row) else None
            if name and str(name).strip().lower() not in skip_values:
                products.append(str(name).strip())

    products = list(dict.fromkeys(products))
    log.info(f"Total unique products to price-check: {len(products)}")
    return products


def main():
    parser = argparse.ArgumentParser(description="Roy G's Spirits Price Tracker")
    parser.add_argument("--file",   required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("Roy G's Spirits Price Tracker — Starting (Both Vendors)")
    log.info("=" * 60)

    products = extract_all_products(args.file)

    # Scrape both vendors for every product
    combined_prices = scrape_all(products)

    log.info("Updating Excel with price comparison...")
    stats = update_excel(
        filepath=args.file,
        combined_prices=combined_prices,
        output_path=args.output,
    )

    log.info("=" * 60)
    log.info("Done!")
    log.info(f"  Products updated : {stats['updated']}")
    log.info(f"  Not matched      : {stats['skipped']}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
