import os
import anthropic
from models import NormalizedMessage

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


def get_drafted_reply(msg: NormalizedMessage) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    user_prompt = f"""Guest name: {msg.guest_name}
Source channel: {msg.source}
Query type: {msg.query_type}
Booking reference: {msg.booking_ref or "Not provided"}
Message: {msg.message_text}

Draft a reply to this guest message."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text