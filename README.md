# Nistula Technical Assessment — Guest Message Handler

## Setup

```bash
cd src
pip install -r requirements.txt
cp ../.env.example ../.env
# Add your ANTHROPIC_API_KEY to .env
uvicorn main:app --reload
```

The server starts at `http://localhost:8000`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhook/message` | Process an inbound guest message |
| GET | `/health` | Health check |

## Test Inputs

**Test 1 — Availability query**
```bash
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "source": "whatsapp",
    "guest_name": "Rahul Sharma",
    "message": "Is the villa available from April 20 to 24? What is the rate for 2 adults?",
    "timestamp": "2026-05-05T10:30:00Z",
    "booking_ref": "NIS-2024-0891",
    "property_id": "villa-b1"
  }'
```

**Test 2 — Post-sales check-in query**
```bash
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "source": "booking_com",
    "guest_name": "Priya Nair",
    "message": "Hi, what time can we check in? Also what is the WiFi password?",
    "timestamp": "2026-05-06T08:00:00Z",
    "booking_ref": "NIS-2024-0910",
    "property_id": "villa-b1"
  }'
```

**Test 3 — Complaint**
```bash
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "source": "airbnb",
    "guest_name": "Arjun Mehta",
    "message": "The AC is not working and it is 35 degrees. This is unacceptable. I want a refund.",
    "timestamp": "2026-05-07T14:00:00Z",
    "booking_ref": "NIS-2024-0925",
    "property_id": "villa-b1"
  }'
```

## Confidence Scoring Logic

Each inbound message receives a confidence score between 0 and 1 that
represents how suitable the AI draft is for sending without human review.

**Base score by query type:**

| Query Type | Base Score | Reasoning |
|---|---|---|
| `post_sales_checkin` | 0.93 | Factual answers (WiFi password, check-in time) — very low ambiguity |
| `pre_sales_availability` | 0.90 | Directly answerable from property context |
| `pre_sales_pricing` | 0.88 | Calculable from known rates |
| `general_enquiry` | 0.80 | Usually answerable but open-ended |
| `special_request` | 0.72 | Needs human confirmation to commit |
| `complaint` | 0.45 | Always requires human judgment |

**Adjustments:**
- Reply under 50 characters → −0.15 (likely an error or incomplete response)
- Reply over 100 characters → +0.02 (signals a substantive answer, capped at 0.98)

**Action thresholds:**
- `auto_send`: score ≥ 0.85 (and not a complaint)
- `agent_review`: score 0.60–0.84
- `escalate`: score < 0.60, or `query_type == complaint` (always)

## Architecture Notes

- **Classifier** uses keyword matching. Fast, transparent, and easy to
  debug. A production version would use a small fine-tuned classifier or
  a Claude call with few-shot examples for better accuracy on edge cases.
- **Normalization** currently handles a uniform payload shape. In
  production, each source channel (Booking.com, Airbnb) sends different
  field names and structures — the normalize function would have
  per-channel adapters to map to the unified schema before any processing.
- **API key** is loaded from `.env` via `python-dotenv` and never
  hardcoded or logged.


  ## Known Limitation
  - The classifier will misclassify some edge cases (a message saying "I'm not happy with the rate" hits complaint before   pricing). In production, we can train a lightweight ML model for classification instead of the current bag of words model.
