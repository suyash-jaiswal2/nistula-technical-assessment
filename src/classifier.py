def classify_query(message: str) -> str:
    """
    Classifies an inbound guest message into one of six query types
    using keyword matching. Order matters: complaint and post-sales
    checks run before the broader availability/pricing checks.
    """
    text = message.lower()

    complaint_keywords = [
        "not working", "broken", "unacceptable", "refund", "complaint",
        "disappointed", "terrible", "awful", "no hot water", "no water",
        "ac not", "no ac", "dirty", "unhappy", "not happy", "this is not"
    ]
    checkin_keywords = [
        "check in", "check-in", "check out", "checkout", "wifi",
        "wi-fi", "password", "arrival", "key", "access code", "instructions"
    ]
    special_keywords = [
        "early check", "late check", "airport", "transfer", "pickup",
        "arrange", "extra bed", "crib", "special request", "decoration"
    ]
    pricing_keywords = [
        "rate", "price", "cost", "how much", "charges", "fee",
        "per night", "tariff", "quote", "total"
    ]
    availability_keywords = [
        "available", "availability", "free", "open", "book",
        "dates", "from", "to", "nights", "stay"
    ]

    if any(k in text for k in complaint_keywords):
        return "complaint"
    if any(k in text for k in checkin_keywords):
        return "post_sales_checkin"
    if any(k in text for k in special_keywords):
        return "special_request"
    if any(k in text for k in pricing_keywords):
        return "pre_sales_pricing"
    if any(k in text for k in availability_keywords):
        return "pre_sales_availability"

    return "general_enquiry"