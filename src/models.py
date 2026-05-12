from pydantic import BaseModel
from typing import Optional


class InboundMessage(BaseModel):
    source: str  # whatsapp | booking_com | airbnb | instagram | direct
    guest_name: str
    message: str
    timestamp: str
    booking_ref: Optional[str] = None
    property_id: Optional[str] = None


class NormalizedMessage(BaseModel):
    message_id: str
    source: str
    guest_name: str
    message_text: str
    timestamp: str
    booking_ref: Optional[str] = None
    property_id: Optional[str] = None
    query_type: str