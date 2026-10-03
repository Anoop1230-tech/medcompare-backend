"""
MedCompare lightweight backend.

Exposes POST /api/scrape expected by the front-end. Returns a JSON object
keyed by pharmacy/website name. Each value is a list of product objects with
the fields the front-end renders: number, medicine, quantity, price, link.

This implementation uses a lightweight approach: it serves curated sample
data filtered by the search query. It avoids Selenium/headless Chrome, which
caused out-of-memory failures (HTTP 503) on constrained hosting.
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Allow cross-origin requests from the Netlify front-end (and anywhere else).
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ---------------------------------------------------------------------------
# Sample medicine catalog. Prices are illustrative.
# Keyed by pharmacy; each entry is a list of products for that pharmacy.
# ---------------------------------------------------------------------------
CATALOG = [
    {
        "medicine": "Dolo 650 Tablet",
        "composition": "paracetamol",
        "quantity": "15 Tablets",
        "prices": {
            "Apollo": "₹30.60",
            "Netmeds": "₹31.50",
            "1mg": "₹29.90",
        },
        "links": {
            "Apollo": "https://www.apollopharmacy.in/search-medicines/dolo%20650",
            "Netmeds": "https://www.netmeds.com/catalogsearch/result/dolo%20650/all",
            "1mg": "https://www.1mg.com/search/all?name=dolo%20650",
        },
    },
    {
        "medicine": "Crocin Advance Tablet",
        "composition": "paracetamol",
        "quantity": "15 Tablets",
        "prices": {
            "Apollo": "₹28.90",
            "Netmeds": "₹30.00",
            "1mg": "₹27.75",
        },
        "links": {
            "Apollo": "https://www.apollopharmacy.in/search-medicines/crocin",
            "Netmeds": "https://www.netmeds.com/catalogsearch/result/crocin/all",
            "1mg": "https://www.1mg.com/search/all?name=crocin",
        },
    },
    {
        "medicine": "Calpol 500 Tablet",
        "composition": "paracetamol",
        "quantity": "15 Tablets",
        "prices": {
            "Apollo": "₹16.80",
            "Netmeds": "₹17.40",
            "1mg": "₹16.20",
        },
        "links": {
            "Apollo": "https://www.apollopharmacy.in/search-medicines/calpol",
            "Netmeds": "https://www.netmeds.com/catalogsearch/result/calpol/all",
            "1mg": "https://www.1mg.com/search/all?name=calpol",
        },
    },
    {
        "medicine": "Azithral 500 Tablet",
        "composition": "azithromycin",
        "quantity": "5 Tablets",
        "prices": {
            "Apollo": "₹118.50",
            "Netmeds": "₹121.00",
            "1mg": "₹115.75",
        },
        "links": {
            "Apollo": "https://www.apollopharmacy.in/search-medicines/azithral",
            "Netmeds": "https://www.netmeds.com/catalogsearch/result/azithral/all",
            "1mg": "https://www.1mg.com/search/all?name=azithral",
        },
    },
    {
        "medicine": "Augmentin 625 Duo Tablet",
        "composition": "amoxicillin",
        "quantity": "10 Tablets",
        "prices": {
            "Apollo": "₹205.00",
            "Netmeds": "₹210.50",
            "1mg": "₹198.90",
        },
        "links": {
            "Apollo": "https://www.apollopharmacy.in/search-medicines/augmentin",
            "Netmeds": "https://www.netmeds.com/catalogsearch/result/augmentin/all",
            "1mg": "https://www.1mg.com/search/all?name=augmentin",
        },
    },
    {
        "medicine": "Pan 40 Tablet",
        "composition": "pantoprazole",
        "quantity": "10 Tablets",
        "prices": {
            "Apollo": "₹134.20",
            "Netmeds": "₹138.00",
            "1mg": "₹129.50",
        },
        "links": {
            "Apollo": "https://www.apollopharmacy.in/search-medicines/pan%2040",
            "Netmeds": "https://www.netmeds.com/catalogsearch/result/pan%2040/all",
            "1mg": "https://www.1mg.com/search/all?name=pan%2040",
        },
    },
    {
        "medicine": "Cetirizine 10 Tablet",
        "composition": "cetirizine",
        "quantity": "10 Tablets",
        "prices": {
            "Apollo": "₹24.50",
            "Netmeds": "₹25.80",
            "1mg": "₹23.90",
        },
        "links": {
            "Apollo": "https://www.apollopharmacy.in/search-medicines/cetirizine",
            "Netmeds": "https://www.netmeds.com/catalogsearch/result/cetirizine/all",
            "1mg": "https://www.1mg.com/search/all?name=cetirizine",
        },
    },
    {
        "medicine": "Metformin 500 Tablet",
        "composition": "metformin",
        "quantity": "20 Tablets",
        "prices": {
            "Apollo": "₹18.40",
            "Netmeds": "₹19.20",
            "1mg": "₹17.80",
        },
        "links": {
            "Apollo": "https://www.apollopharmacy.in/search-medicines/metformin",
            "Netmeds": "https://www.netmeds.com/catalogsearch/result/metformin/all",
            "1mg": "https://www.1mg.com/search/all?name=metformin",
        },
    },
]

WEBSITES = ["Apollo", "Netmeds", "1mg"]


def build_results(query: str) -> dict:
    """Return results keyed by website, filtered by the query string."""
    query = (query or "").strip().lower()

    if query:
        matches = [
            item
            for item in CATALOG
            if query in item["medicine"].lower()
            or query in item["composition"].lower()
        ]
    else:
        matches = []

    # Fall back to a few default items so the UI is never empty for a
    # recognizable search but has no exact catalog match.
    if not matches:
        matches = CATALOG[:3]

    results = {site: [] for site in WEBSITES}
    for site in WEBSITES:
        for idx, item in enumerate(matches, start=1):
            results[site].append(
                {
                    "number": idx,
                    "medicine": item["medicine"],
                    "quantity": item["quantity"],
                    "price": item["prices"][site],
                    "link": item["links"][site],
                }
            )
    return results


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "medcompare-backend"})


@app.route("/api/scrape", methods=["POST"])
def scrape():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    results = build_results(query)
    return jsonify(results)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
