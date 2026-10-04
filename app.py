"""
MedCompare backend — LIVE medicine price lookup.

Exposes POST /api/scrape expected by the front-end. Returns a JSON object
keyed by source name. Each value is a list of product objects with the fields
the front-end renders: number, medicine, quantity, price, link.

Live data source:
- Tata 1mg public search API (https://www.1mg.com/pwa-api/...). This returns
  REAL, current product names, pack sizes, prices and product URLs. It works
  with plain HTTP requests (no headless browser), which keeps the service
  light enough to run on constrained hosting.

Note on other pharmacies:
- Apollo and Netmeds render prices client-side via JavaScript and do not
  expose a simple public price API, so they cannot be scraped reliably with
  lightweight requests. Rather than show fake numbers, this backend returns
  live 1mg data only. The response is keyed by "1mg (Tata)".
"""

import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

ONEMG_SEARCH_URL = "https://www.1mg.com/pwa-api/api/v4/search/all"
ONEMG_BASE = "https://www.1mg.com"
DEFAULT_CITY = os.environ.get("ONEMG_CITY", "Gurgaon")
REQUEST_TIMEOUT = 20

SOURCE_NAME = "1mg (Tata)"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def fetch_1mg(query: str, limit: int = 10):
    """Fetch real products with prices from the 1mg public search API."""
    headers = dict(HEADERS)
    headers["X-City"] = DEFAULT_CITY
    params = {
        "q": query,
        "page_number": 1,
        "per_page": limit,
        "types[]": ["allopathy", "sku"],
        "city": DEFAULT_CITY,
    }
    resp = requests.get(
        ONEMG_SEARCH_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    payload = resp.json()

    results = []
    search_results = (payload.get("data") or {}).get("search_results") or []
    number = 0
    for item in search_results:
        if item.get("type") != "drug":
            continue

        prices = item.get("prices") or {}
        # Prefer the actual selling (discounted) price; fall back to MRP.
        price = prices.get("discounted_price") or prices.get("mrp")
        if not price:
            continue

        name = (item.get("name") or "").replace("<b>", "").replace("</b>", "").strip()
        if not name:
            continue

        qinfo = item.get("quantity_info") or {}
        sell_qty = qinfo.get("selling_quantity")
        quantity = f"{sell_qty} units" if sell_qty else "1 unit"

        url_path = item.get("url") or ""
        link = (ONEMG_BASE + url_path) if url_path.startswith("/") else (url_path or ONEMG_BASE)

        number += 1
        results.append(
            {
                "number": number,
                "medicine": name,
                "quantity": quantity,
                "price": str(price),
                "link": link,
            }
        )

    return results


def build_results(query: str) -> dict:
    """Return results keyed by source for the given query."""
    query = (query or "").strip()
    if not query:
        return {SOURCE_NAME: []}

    try:
        products = fetch_1mg(query)
    except requests.RequestException as exc:
        # Surface a clean error the front-end can display.
        return {"error": f"Live lookup failed: {exc}"}

    return {SOURCE_NAME: products}


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "medcompare-backend", "source": SOURCE_NAME})


@app.route("/api/scrape", methods=["POST"])
def scrape():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    return jsonify(build_results(query))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
