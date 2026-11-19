# MedCompare Backend

Lightweight Flask API that powers the MedCompare front-end.

## Live sources

| Source (response key) | Data source | Status |
|---|---|---|
| `1mg (Tata)` | Tata 1mg public search API | Live |
| `PharmEasy` | PharmEasy public search API | Live |
| `Netmeds` | Netmeds public search API | Live |
| `Apollo Pharmacy` | Apollo search API, using the anonymous guest token the site issues to every visitor | Live |

MedPlus is not supported: medplusmart.com blocks non-browser requests (Akamai 403).

## Endpoint

### `POST /api/scrape`
Request body:
```json
{ "query": "paracetamol" }
```

Response: an object keyed by pharmacy name. Each value is a list of products:
```json
{
  "1mg (Tata)": [
    { "number": 1, "medicine": "Dolo 650 Tablet", "quantity": "15 units", "price": "₹29.7", "link": "https://www.1mg.com/drugs/..." }
  ],
  "PharmEasy": [ ... ],
  "Netmeds": [ ... ],
  "Apollo Pharmacy": [ ... ]
}
```
If a source fails or times out, its list is empty and the other sources are still returned.

### `GET /`
Health check. Lists the active sources.

## Run locally
```bash
pip install -r requirements.txt
python app.py
# or production-style:
gunicorn app:app
```

## Environment variables
- `PORT`: port to listen on (default 5000)
- `ONEMG_CITY`: city sent to 1mg (default `Gurgaon`)
- `APOLLO_PINCODE`: pincode sent to Apollo (default empty)

## Adding a pharmacy
1. Write a `fetch_<name>(query, limit=10)` function in `app.py` that returns a list of
   `{"medicine", "quantity", "price", "link"}` dicts.
2. Register it in the `SOURCES` dict. The key is the name shown on the website.
3. Add a chart color for the same name in the front-end `scripts.js` `colors` map.

## Notes
All sources are fetched with plain HTTP requests in parallel. The service
intentionally avoids Selenium/headless Chrome, which caused out-of-memory
failures (HTTP 503) on constrained hosting.

The Apollo guest token lasts 12 hours. It is cached in memory, refreshed
10 minutes before it expires, and fetched again if Apollo returns 401.

## Troubleshooting
- **Apollo shows `SSLError: CERTIFICATE_VERIFY_FAILED` when testing locally:**
  a network firewall (for example Sophos on a college or office network) is
  intercepting `apigateway.apollo247.in`. Test on a different network, such as
  a mobile hotspot. The deployed Render service is not affected.
- **One pharmacy returns an empty list:** that site was slow, down or changed its
  API. The other pharmacies are still returned.
