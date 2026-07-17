"""
Scrapes the UOB Gold and Silver Prices page for the "Argor Cast Bar" row
(Bank Sells (SGD) / Bank Buys (SGD)) and appends a timestamped reading to
docs/data/prices.json.

The rates table on the UOB page is populated by JavaScript after the page
loads, so a plain HTTP request won't see the numbers -- we need a real
(headless) browser to render the page first. That's what Playwright does.

Usage:
    python scrape.py

Exit codes:
    0  success, new reading appended
    1  could not find the Argor Cast Bar row (page structure may have
       changed, or the page failed to load) -- existing data file is left
       untouched so a single failed run never corrupts history.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://www.uobgroup.com/online-rates/gold-and-silver-prices.page"
DATA_FILE = Path(__file__).resolve().parent.parent / "docs" / "data" / "prices.json"

# Row label we're looking for. UOB's exact wording has shifted before
# (e.g. "1oz Argor Cast Bar" vs "Argor Cast Bar"), so we match loosely.
ROW_PATTERN = re.compile(r"argor.*cast.*bar", re.IGNORECASE)

# Matches numbers like "3,456.78" or "3456.78"
NUMBER_PATTERN = re.compile(r"[\d,]+\.\d+")


def parse_number(text: str) -> float | None:
    match = NUMBER_PATTERN.search(text)
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def scrape() -> tuple[float, float]:
    """Returns (bank_sells, bank_buys) for the Argor Cast Bar row."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60_000)

        # Wait for the rates table to actually have data rows (not just
        # the empty header). If this times out, the site likely changed
        # or blocked us.
        page.wait_for_function(
            "document.querySelectorAll('table tr').length > 1",
            timeout=30_000,
        )

        rows = page.query_selector_all("table tr")
        target_cells = None
        for row in rows:
            cells = row.query_selector_all("td, th")
            cell_texts = [c.inner_text().strip() for c in cells]
            row_text = " ".join(cell_texts)
            if ROW_PATTERN.search(row_text):
                target_cells = cell_texts
                break

        browser.close()

    if not target_cells:
        raise RuntimeError(
            "Could not find an 'Argor Cast Bar' row in the rendered page. "
            "The table structure may have changed."
        )

    # Expected columns: DESCRIPTION | UNIT | BANK SELLS (SGD) | BANK BUYS (SGD)
    # We parse defensively by scanning all numeric-looking cells rather than
    # trusting fixed column positions.
    numbers = [n for n in (parse_number(c) for c in target_cells) if n is not None]
    if len(numbers) < 2:
        raise RuntimeError(
            f"Found the Argor Cast Bar row but couldn't parse two prices "
            f"from it: {target_cells!r}"
        )

    bank_sells, bank_buys = numbers[0], numbers[1]
    return bank_sells, bank_buys


def append_reading(bank_sells: float, bank_buys: float) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    if DATA_FILE.exists():
        history = json.loads(DATA_FILE.read_text())
    else:
        history = []

    history.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "bank_sells_sgd": bank_sells,
            "bank_buys_sgd": bank_buys,
        }
    )

    DATA_FILE.write_text(json.dumps(history, indent=2))


def main() -> int:
    try:
        bank_sells, bank_buys = scrape()
    except Exception as exc:  # noqa: BLE001 - we want to log any failure
        print(f"Scrape failed: {exc}", file=sys.stderr)
        return 1

    append_reading(bank_sells, bank_buys)
    print(f"Recorded Argor Cast Bar: Sells={bank_sells} Buys={bank_buys}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
