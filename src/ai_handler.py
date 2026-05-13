import os
import logging
import anthropic
from groq import Groq
from models import NormalizedMessage

logger = logging.getLogger(__name__)

PROPERTY_CONTEXT = """
Property: Villa B1, Assagao, North Goa
Bedrooms: 3 | Max guests: 6 | Private pool: Yes
Check-in: 2pm | Check-out: 11am
Base rate: INR 18,000 per night (up to 4 guests)
Extra guest: INR 2,000 per night per person
WiFi password: Nistula@2024
Caretaker: Available 8am to 10pm
Chef on call: Yes, pre-booking required
Availability April 20-24: Available
Cancellation: Free up to 7 days before check-in
"""

SYSTEM_PROMPT = f"""You are a warm, professional guest relations assistant for Nistula, \
a luxury villa rental company in Goa, India.

Property context:
{PROPERTY_CONTEXT}

Guidelines:
- Keep replies concise (3-6 sentences), friendly, and helpful.
- Address the guest by their first name only.
- For complaints, be empathetic first — do not make promises about refunds.
- Do not invent information that is not in the property context.
- Always sign off as "— Nistula Team".
"""


def _build_user_prompt(msg: NormalizedMessage) -> str:
    return f"""Guest name: {msg.guest_name}
Source channel: {msg.source}
Query type: {msg.query_type}
Booking reference: {msg.booking_ref or "Not provided"}
Message: {msg.message_text}

Draft a reply to this guest message."""


def _try_anthropic(user_prompt: str) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def _try_groq(user_prompt: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=500,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def get_drafted_reply(msg: NormalizedMessage) -> tuple[str, str]:
    """
    Returns (drafted_reply, provider_used).
    Tries Anthropic first. If it fails for any reason, falls back to Groq.
    """
    user_prompt = _build_user_prompt(msg)

    try:
        reply = _try_anthropic(user_prompt)
        logger.info("Reply generated via Anthropic.")
        return reply, "anthropic"
    except Exception as e:
        logger.warning(f"Anthropic failed ({e}). Falling back to Groq.")

    try:
        reply = _try_groq(user_prompt)
        logger.info("Reply generated via Groq (fallback).")
        return reply, "groq"
    except Exception as e:
        logger.error(f"Groq also failed: {e}")
        raise RuntimeError("Both Anthropic and Groq are unavailable.") from e