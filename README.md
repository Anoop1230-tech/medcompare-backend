# MedCompare Backend

Lightweight Flask API that powers the MedCompare front-end.

## Endpoint

### `POST /api/scrape`
Request body:
```json
{ "query": "paracetamol" }
```

Response: an object keyed by pharmacy name. Each value is a list of products:
```json
{
  "Apollo": [
    { "number": 1, "medicine": "Dolo 650 Tablet", "quantity": "15 Tablets", "price": "₹30.60", "link": "https://..." }
  ],
  "Netmeds": [ ... ],
  "1mg": [ ... ]
}
```

### `GET /`
Health check.

## Run locally
```bash
pip install -r requirements.txt
python app.py
# or production-style:
gunicorn app:app
```

## Notes
This service serves curated sample data filtered by the search query. It
intentionally avoids Selenium/headless Chrome, which caused out-of-memory
failures (HTTP 503) on constrained hosting.
