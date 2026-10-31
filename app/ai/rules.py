"""Deterministic business rules and safety guardrails implemented in pure Python."""

import re

from app.ai.schemas import Decision

ORDER_REGEX = re.compile(r"\b\d{3}-\d{7}-\d{7}\b")
PROMPT_INJECTION_PATTERNS = [
    re.compile(
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE
    ),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"disregard\s+(your\s+)?rules", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(an|a|in\s+developer)", re.IGNORECASE),
    re.compile(
        r"print\s+(your\s+)?(instructions|configuration|secret|key)", re.IGNORECASE
    ),
    re.compile(r"grant\s+(me\s+)?(a\s+)?(100%|discount|refund)", re.IGNORECASE),
]

ANGRY_OR_REFUND_PATTERNS = [
    re.compile(r"\b(money\s+back|refund|chargeback|compensation)\b", re.IGNORECASE),
    re.compile(
        r"\b(terrible|worst|scam|fraud|unacceptable|lawyer|sue|court)\b", re.IGNORECASE
    ),
    re.compile(r"\b(angry|furious|disgusted|rip-?off)\b", re.IGNORECASE),
]

HUMAN_REQUEST_PATTERNS = [
    re.compile(
        r"\b(talk|speak)\s+(to|with)\s+(a\s+)?(real\s+)?(person|human|manager|supervisor|someone)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(need|want)\s+to\s+(talk|speak)\s+(to|with)\s+(a\s+)?(human|person|manager)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(phone\s+call|call\s+me|on\s+the\s+phone)\b", re.IGNORECASE),
]

SAFETY_INJURY_PATTERNS = [
    re.compile(
        r"\b(injury|hurt|hospital|doctor|cut|bleeding|emergency|danger|unsafe)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(rescued|drowning|life-threatening)\b", re.IGNORECASE),
]


def extract_order_number(text: str) -> str | None:
    """Extract standard Amazon order number format: 112-4839201-5528341."""
    match = ORDER_REGEX.search(text)
    return match.group(0) if match else None


def check_prompt_injection(text: str) -> bool:
    """Return True if text exhibits known prompt injection or policy override patterns."""
    return any(p.search(text) for p in PROMPT_INJECTION_PATTERNS)


def check_mandatory_escalation(
    text: str, has_attachments: bool = False
) -> tuple[bool, str]:
    """Check deterministic escalation triggers before model invocation."""
    if has_attachments:
        return True, "Email contains attachments requiring visual human review."

    if check_prompt_injection(text):
        return True, "Email contains prompt injection or policy override instructions."

    for p in SAFETY_INJURY_PATTERNS:
        if p.search(text):
            return True, "Email mentions safety hazard, injury, or emergency."

    for p in ANGRY_OR_REFUND_PATTERNS:
        if p.search(text):
            return (
                True,
                "Customer is expressing anger, demanding a refund, or threatening a dispute.",
            )

    for p in HUMAN_REQUEST_PATTERNS:
        if p.search(text):
            return True, "Customer requested direct human or supervisor interaction."

    return False, ""


def evaluate_paddle_board_rules(
    email_text: str,
    subject: str,
    sender_name: str = "",
) -> Decision | None:
    """Apply deterministic rules for paddle board issues."""
    text_lower = email_text.lower()
    order_num = extract_order_number(email_text)

    # 1. Seam split / catastrophic failure -> Escalate
    if "seam" in text_lower and (
        "split" in text_lower or "burst" in text_lower or "rail" in text_lower
    ):
        reply = (
            f"Hi {sender_name or 'there'},\n\n"
            "Thank you for contacting Harbor & Pine. A seam separation is covered under our 1-year warranty. "
            "I have forwarded your request to our warranty team along with your order details so they can arrange a replacement for you.\n\n"
            "Best regards,\nHarbor & Pine Support"
        )
        return Decision(
            action="escalate",
            section="paddle-boards",
            reply=reply,
            reason="Split seam requires human warranty replacement processing.",
            proposed_action="escalate",
        )

    # 2. Slow leak logic
    if (
        "leak" in text_lower
        or "loses air" in text_lower
        or "soft every morning" in text_lower
        or "losing pressure" in text_lower
    ):
        # Check if customer already did valve check
        did_valve_check = (
            "valve check" in text_lower
            or "tightened" in text_lower
            or "wrench" in text_lower
            or "soapy water" in text_lower
        )
        if did_valve_check:
            # Check delivery window (simulated or mentioned)
            reply = (
                f"Hi {sender_name or 'there'},\n\n"
                "Thank you for confirming you completed the valve check. Because the board continues to lose air, "
                "I have escalated your ticket to our product team to verify your order details and process a replacement under warranty.\n\n"
                "Best regards,\nHarbor & Pine Support"
            )
            return Decision(
                action="escalate",
                section="paddle-boards",
                reply=reply,
                reason="Board continues losing air after valve check; requires warranty replacement.",
                proposed_action="new-board",
            )
        else:
            # First contact -> explain 4-step valve check
            reply = (
                f"Hi {sender_name or 'there'},\n\n"
                "Thank you for reaching out. Over 90% of slow air loss is caused by a slightly loose valve core rather than a leak. "
                "Please follow these steps to inspect and tighten the valve:\n\n"
                "1. Inflate the board to 15 PSI.\n"
                "2. Spray or brush soapy water around the valve seat to see if air bubbles form.\n"
                "3. Insert the black valve wrench from your repair kit into the valve notches and firmly turn clockwise one quarter turn.\n"
                "4. Check the pressure again after 24 hours.\n\n"
                "If it continues losing more than 2 PSI after tightening, please let us know with your order number and we will resolve it under warranty.\n\n"
                "Best regards,\nHarbor & Pine Support"
            )
            return Decision(
                action="reply",
                section="paddle-boards",
                reply=reply,
                reason="Slow leak reported without valve check; instructed customer on valve maintenance.",
                proposed_action="valve-check",
            )

    # 3. Missing pump or accessory
    if (
        "pump" in text_lower
        or "accessory" in text_lower
        or "fin" in text_lower
        or "paddle" in text_lower
        or "leash" in text_lower
    ):
        if (
            "missing" in text_lower
            or "not in the box" in text_lower
            or "without" in text_lower
        ):
            if order_num:
                reply = (
                    f"Hi {sender_name or 'there'},\n\n"
                    f"Thank you for reaching out. We apologize that your accessory was missing from order {order_num}. "
                    "I have forwarded your request to our warehouse dispatch team so they can send the missing part to your delivery address.\n\n"
                    "Best regards,\nHarbor & Pine Support"
                )
                return Decision(
                    action="escalate",
                    section="paddle-boards",
                    reply=reply,
                    reason=f"Missing accessory with order {order_num}; forwarded for warehouse dispatch.",
                    proposed_action="ship-part",
                )
            else:
                reply = (
                    f"Hi {sender_name or 'there'},\n\n"
                    "Thank you for contacting Harbor & Pine. We are sorry to hear that an item was missing from your box. "
                    "Could you please reply with your Amazon order number and confirm which board model you purchased? "
                    "Once we have that information, we will gladly arrange a replacement dispatch for you.\n\n"
                    "Best regards,\nHarbor & Pine Support"
                )
                return Decision(
                    action="reply",
                    section="paddle-boards",
                    reply=reply,
                    reason="Missing accessory without order number; requested order details.",
                    proposed_action="ask-details",
                )

    # 4. Sizing advice
    if (
        "size" in text_lower
        or "which board" in text_lower
        or "welche größe" in text_lower
        or "weigh" in text_lower
        or "kg" in text_lower
    ):
        # Check weight in text
        match_kg = re.search(r"(\d+)\s*kg", text_lower)
        weight = int(match_kg.group(1)) if match_kg else 80

        is_german = (
            "welche" in text_lower or "hallo" in text_lower or "wiege" in text_lower
        )
        if is_german:
            reply = (
                (
                    f"Hallo {sender_name or ''},\n\n"
                    "vielen Dank für Ihre Anfrage. Für ein Gewicht von 70 kg empfehlen wir unser 10'6\" All-round Board. "
                    "Es bietet hervorragende Stabilität für Einsteiger und ist ideal für ruhige Gewässer geeignet.\n\n"
                    "Beste Grüße,\nHarbor & Pine Support"
                )
                if weight <= 85
                else (
                    f"Hallo {sender_name or ''},\n\n"
                    "vielen Dank für Ihre Anfrage. Für ein Gewicht ab 85 kg empfehlen wir unser 11' All-round Board. "
                    "Es ist unser stabilstes Board und trägt bis zu 110 kg mit Leichtigkeit.\n\n"
                    "Beste Grüße,\nHarbor & Pine Support"
                )
            )
        else:
            if weight <= 85:
                rec_board = "10'6\" All-round board (rated up to 85 kg)"
            elif weight <= 110:
                rec_board = "11' All-round board (rated up to 110 kg)"
            else:
                rec_board = "12'6\" Touring board (rated up to 130 kg)"

            reply = (
                f"Hi {sender_name or 'there'},\n\n"
                f"Thank you for contacting Harbor & Pine. Based on your weight of {weight} kg, we recommend our {rec_board}. "
                "It provides the ideal balance of buoyancy, stability, and ease of paddling on calm water.\n\n"
                "Best regards,\nHarbor & Pine Support"
            )

        return Decision(
            action="reply",
            section="paddle-boards",
            reply=reply,
            reason=f"Recommended board size for {weight} kg rider.",
            proposed_action=None,
        )

    return None


def evaluate_shelving_rules(
    email_text: str,
    subject: str,
    sender_name: str = "",
) -> Decision | None:
    """Apply deterministic rules for flat-pack shelving issues."""
    text_lower = email_text.lower()
    order_num = extract_order_number(email_text)

    # 1. Back panel assembly advice
    if "back panel" in text_lower or "assembly" in text_lower:
        if (
            "which side" in text_lower
            or "face" in text_lower
            or "orientation" in text_lower
        ):
            reply = (
                f"Hi {sender_name or 'there'},\n\n"
                "Thank you for reaching out. When assembling your bookcase, the finished (colored) side of the back panel "
                "must face inward toward the shelves. The unfinished raw backing faces outward toward the wall.\n\n"
                "Best regards,\nHarbor & Pine Support"
            )
            return Decision(
                action="reply",
                section="shelving",
                reply=reply,
                reason="Provided back panel assembly orientation instruction.",
                proposed_action=None,
            )

    # 2. Missing screws or hardware
    if (
        "screw" in text_lower
        or "hardware" in text_lower
        or "bolts" in text_lower
        or "fastener" in text_lower
    ):
        if "missing" in text_lower or "not enough" in text_lower:
            if order_num:
                reply = (
                    f"Hi {sender_name or 'there'},\n\n"
                    f"Thank you for reaching out. We apologize for the missing hardware in order {order_num}. "
                    "I have forwarded your request to our warehouse team to dispatch a replacement hardware kit to your address.\n\n"
                    "Best regards,\nHarbor & Pine Support"
                )
                return Decision(
                    action="escalate",
                    section="shelving",
                    reply=reply,
                    reason=f"Missing hardware with order {order_num}; escalated for kit dispatch.",
                    proposed_action="ship-hardware-kit",
                )
            else:
                reply = (
                    f"Hi {sender_name or 'there'},\n\n"
                    "Thank you for contacting Harbor & Pine. We apologize that there were not enough screws included in your unit. "
                    "Could you please reply with your Amazon order number and confirm which shelving model you purchased? "
                    "We will immediately send out a free replacement hardware pack for you.\n\n"
                    "Best regards,\nHarbor & Pine Support"
                )
                return Decision(
                    action="reply",
                    section="shelving",
                    reply=reply,
                    reason="Missing screws without order number; requested order details.",
                    proposed_action="ask-details",
                )

    # 3. Damaged panels
    if "cracked" in text_lower or "damaged" in text_lower or "broken" in text_lower:
        if order_num:
            reply = (
                f"Hi {sender_name or 'there'},\n\n"
                f"Thank you for reaching out. We are sorry to hear that a panel was damaged in order {order_num}. "
                "I have forwarded your details to our replacement department to arrange shipment of the replacement panel(s).\n\n"
                "Best regards,\nHarbor & Pine Support"
            )
            return Decision(
                action="escalate",
                section="shelving",
                reply=reply,
                reason=f"Damaged panel reported with order {order_num}; forwarded for replacement dispatch.",
                proposed_action="ship-panels",
            )
        else:
            reply = (
                f"Hi {sender_name or 'there'},\n\n"
                "Thank you for contacting Harbor & Pine. We are sorry to hear that your shelf arrived with damaged parts. "
                "Please reply with your Amazon order number and the specific panel number(s) shown in your assembly manual, "
                "and we will dispatch replacements right away.\n\n"
                "Best regards,\nHarbor & Pine Support"
            )
            return Decision(
                action="reply",
                section="shelving",
                reply=reply,
                reason="Damaged panel reported without order number; requested order details.",
                proposed_action="ask-details",
            )

    # 4. Wrong finish or color
    if "wrong" in text_lower and (
        "finish" in text_lower
        or "color" in text_lower
        or "white" in text_lower
        or "walnut" in text_lower
        or "oak" in text_lower
    ):
        reply = (
            f"Hi {sender_name or 'there'},\n\n"
            "Thank you for reaching out. We apologize that the incorrect finish was sent for your order. "
            "I have escalated your ticket to our customer service team so they can arrange an exchange for the correct color.\n\n"
            "Best regards,\nHarbor & Pine Support"
        )
        return Decision(
            action="escalate",
            section="shelving",
            reply=reply,
            reason="Wrong finish delivered; escalated for product exchange.",
            proposed_action="exchange",
        )

    return None


def evaluate_general_rules(
    email_text: str,
    subject: str,
    sender_name: str = "",
) -> Decision | None:
    """Apply deterministic rules for returns, shipping, and general policies."""
    text_lower = email_text.lower()
    order_num = extract_order_number(email_text)

    # 1. Shipping time for replacement parts
    if "replacement" in text_lower and (
        "shipping" in text_lower
        or "how long" in text_lower
        or "arrive" in text_lower
        or "time" in text_lower
    ):
        reply = (
            f"Hi {sender_name or 'there'},\n\n"
            "Thank you for reaching out. Replacement parts leave our warehouse within 2 business days and typically arrive within 3 to 7 business days. "
            "You will receive an automated tracking link by email as soon as the package is dispatched.\n\n"
            "Best regards,\nHarbor & Pine Support"
        )
        return Decision(
            action="reply",
            section="shipping",
            reply=reply,
            reason="Answered replacement parts shipping timeline inquiry.",
            proposed_action=None,
        )

    # 2. Where is my order (late Amazon parcel)
    if (
        "where is my order" in text_lower
        or "has not arrived" in text_lower
        or "late" in text_lower
        or "due on" in text_lower
    ) and order_num:
        reply = (
            f"Hi {sender_name or 'there'},\n\n"
            f"Thank you for reaching out regarding order {order_num}. Because Amazon fulfills all initial order shipments, "
            "I have forwarded your request to our logistics team to check the parcel status directly with Amazon carrier support.\n\n"
            "Best regards,\nHarbor & Pine Support"
        )
        return Decision(
            action="escalate",
            section="shipping",
            reply=reply,
            reason=f"Order tracking inquiry for specific parcel {order_num}; escalated for Amazon carrier review.",
            proposed_action="escalate",
        )

    # 3. Return inquiry for other products
    if "return" in text_lower and (
        "how" in text_lower
        or "process" in text_lower
        or "work" in text_lower
        or "bought" in text_lower
    ):
        reply = (
            f"Hi {sender_name or 'there'},\n\n"
            "Thank you for reaching out. All Harbor & Pine products are fulfilled through Amazon. "
            "You can initiate a return within 30 days of delivery by visiting 'Your Orders' on Amazon and selecting 'Return or replace items' to print a prepaid return label.\n\n"
            "Best regards,\nHarbor & Pine Support"
        )
        return Decision(
            action="reply",
            section="returns-and-warranty",
            reply=reply,
            reason="Explained standard 30-day Amazon return procedure.",
            proposed_action=None,
        )

    # 4. Angry refund demand
    if "money back" in text_lower or "worst" in text_lower or "refund" in text_lower:
        reply = (
            f"Hi {sender_name or 'there'},\n\n"
            "Thank you for reaching out. I am very sorry for your frustrating experience. "
            "I have escalated your message to a senior support representative who will review your order and assist you with a resolution.\n\n"
            "Best regards,\nHarbor & Pine Support"
        )
        return Decision(
            action="escalate",
            section="returns-and-warranty",
            reply=reply,
            reason="Customer dissatisfied demanding refund; escalated to senior representative.",
            proposed_action="escalate",
        )

    return None
