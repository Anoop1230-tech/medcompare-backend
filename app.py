"""
MedCompare backend — LIVE medicine price lookup.

Exposes POST /api/scrape expected by the front-end. Returns a JSON object
keyed by source name. Each value is a list of product objects with the fields
the front-end renders: number, medicine, quantity, price, link.

Live data sources (both return REAL current prices via plain HTTP requests,
no headless browser required):
- Tata 1mg public search API      (https://www.1mg.com/pwa-api/...)
- PharmEasy public search API      (https://pharmeasy.in/api/search/...)

Apollo and Netmeds are intentionally not included: they gate their price
APIs behind API keys / signed requests and render prices client-side, so they
cannot be scraped reliably with lightweight requests. Rather than show fake
numbers, only verified live sources are returned.
"""

import os
import concurrent.futures
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

REQUEST_TIMEOUT = 20
DEFAULT_CITY = os.environ.get("ONEMG_CITY", "Gurgaon")

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ---------------------------------------------------------------------------
# Source: Tata 1mg
# ---------------------------------------------------------------------------
ONEMG_URL = "https://www.1mg.com/pwa-api/api/v4/search/all"
ONEMG_BASE = "https://www.1mg.com"


def fetch_1mg(query: str, limit: int = 10):
    headers = dict(BASE_HEADERS)
    headers["X-City"] = DEFAULT_CITY
    params = {
        "q": query,
        "page_number": 1,
        "per_page": limit,
        "types[]": ["allopathy", "sku"],
        "city": DEFAULT_CITY,
    }
    resp = requests.get(ONEMG_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()

    out = []
    results = (payload.get("data") or {}).get("search_results") or []
    for item in results:
        if item.get("type") != "drug":
            continue
        prices = item.get("prices") or {}
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
        out.append({"medicine": name, "quantity": quantity, "price": str(price), "link": link})
    return out


# ---------------------------------------------------------------------------
# Source: PharmEasy
# ---------------------------------------------------------------------------
PHARMEASY_URL = "https://pharmeasy.in/api/search/search/"
PHARMEASY_PRODUCT_BASE = "https://pharmeasy.in/online-medicine-order/"


def fetch_pharmeasy(query: str, limit: int = 10):
    resp = requests.get(
        PHARMEASY_URL,
        headers=BASE_HEADERS,
        params={"q": query, "page": 1},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()

    out = []
    products = (payload.get("data") or {}).get("products") or []
    for p in products[:limit]:
        name = (p.get("name") or "").strip()
        price = p.get("salePriceDecimal") or p.get("mrpDecimal")
        if not name or not price:
            continue
        quantity = p.get("measurementUnit") or "1 unit"
        slug = p.get("slug") or ""
        link = (PHARMEASY_PRODUCT_BASE + slug) if slug else "https://pharmeasy.in"
        out.append(
            {"medicine": name, "quantity": quantity, "price": f"\u20b9{price}", "link": link}
        )
    return out


# ---------------------------------------------------------------------------
SOURCES = {
    "1mg (Tata)": fetch_1mg,
    "PharmEasy": fetch_pharmeasy,
}


def build_results(query: str) -> dict:
    query = (query or "").strip()
    results = {name: [] for name in SOURCES}
    if not query:
        return results

    def run(name_fn):
        name, fn = name_fn
        try:
            items = fn(query)
        except Exception:
            items = []
        # Attach display numbers per source.
        return name, [dict(number=i + 1, **it) for i, it in enumerate(items)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(SOURCES)) as ex:
        for name, items in ex.map(run, SOURCES.items()):
            results[name] = items

    return results


@app.route("/", methods=["GET"])
def health():
    return jsonify(
        {"status": "ok", "service": "medcompare-backend", "sources": list(SOURCES.keys())}
    )


@app.route("/api/scrape", methods=["POST"])
def scrape():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    return jsonify(build_results(query))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
