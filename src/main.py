import uuid
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from models import InboundMessage, NormalizedMessage
from classifier import classify_query
from ai_handler import get_drafted_reply

load_dotenv()

app = FastAPI(title="Nistula Guest Message Handler")

VALID_SOURCES = {"whatsapp", "booking_com", "airbnb", "instagram", "direct"}


# --- Helpers ---

def normalize(payload: InboundMessage, message_id: str, query_type: str) -> NormalizedMessage:
    """
    Maps the raw inbound payload to the unified internal schema.
    In production this would also handle per-channel field name differences
    (e.g. Booking.com sends 'guest_first_name' + 'guest_last_name').
    """
    return NormalizedMessage(
        message_id=message_id,
        source=payload.source,
        guest_name=payload.guest_name,
        message_text=payload.message,
        timestamp=payload.timestamp,
        booking_ref=payload.booking_ref,
        property_id=payload.property_id,
        query_type=query_type,
    )


def compute_confidence(query_type: str, reply: str) -> float:
    """
    Confidence scoring logic — see README for full explanation.
    Base score is driven by query type predictability.
    Minor adjustments for reply length as a quality signal.
    """
    base_scores = {
        "post_sales_checkin": 0.93,   # Factual: WiFi, check-in time — low ambiguity
        "pre_sales_availability":  0.90,  # Property context covers it directly
        "pre_sales_pricing": 0.88,    # Calculable from known rates
        "general_enquiry": 0.80,      # Usually answerable but open-ended
        "special_request": 0.72,      # Needs human confirmation in practice
        "complaint": 0.45,            # Always requires human judgment
    }
    score = base_scores.get(query_type, 0.70)

    # Very short reply likely means something went wrong
    if len(reply) < 50:
        score -= 0.15
    # Reasonable length is a positive signal
    elif len(reply) > 100:
        score = min(score + 0.02, 0.98)

    return round(score, 2)


def determine_action(query_type: str, confidence: float) -> str:
    if query_type == "complaint":
        return "escalate"
    if confidence >= 0.85:
        return "auto_send"
    if confidence >= 0.60:
        return "agent_review"
    return "escalate"


# --- Endpoints ---

@app.post("/webhook/message")
async def handle_message(payload: InboundMessage):
    if payload.source not in VALID_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source '{payload.source}'. Must be one of: {VALID_SOURCES}",
        )

    try:
        message_id = str(uuid.uuid4())
        query_type = classify_query(payload.message)
        normalized = normalize(payload, message_id, query_type)
        drafted_reply, provider = get_drafted_reply(normalized)
        confidence = compute_confidence(query_type, drafted_reply)
        action = determine_action(query_type, confidence)

        return {
            "message_id": message_id,
            "query_type": query_type,
            "drafted_reply": drafted_reply,
            "confidence_score": confidence,
            "action": action,
            "provider": provider,   # "anthropic" or "groq" — useful to show in demo
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}