"""All derived numbers live here so the web form, the database views and the PDF agree."""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

ZERO = Decimal("0.00")
CGST_RATE = Decimal("2.5")
SGST_RATE = Decimal("2.5")
IGST_RATE = Decimal("5")

GSTIN_RE = re.compile(r"^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

STATUS_PENDING = "Payment Pending"
STATUS_ADVANCE = "Advance Paid"
STATUS_PAID = "Fully Paid"


def q2(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_money(raw):
    """'₹ 36,500.00' -> Decimal('36500.00'); blank -> 0. Raises ValueError on junk."""
    text = str(raw or "").replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    if not text:
        return ZERO
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(raw)
    if value < 0:
        raise ValueError(raw)
    return q2(value)


def inr(value, symbol=True):
    """Indian digit grouping: 1234567.5 -> '₹12,34,567.50'. Paise shown only when non-zero."""
    value = q2(value or 0)
    negative = value < 0
    whole, frac = f"{abs(value):.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    text = whole if frac == "00" else f"{whole}.{frac}"
    if symbol:
        text = "₹" + text
    return ("-" if negative else "") + text


def trip_length(start, end):
    """Inclusive day count and night count. 02 Jan -> 07 Jan = 6 days / 5 nights."""
    if not start or not end or end < start:
        return 0, 0
    nights = (end - start).days
    return nights + 1, nights


def plural(n, one, many):
    return one if n == 1 else many


def duration_label(days, nights):
    if not days:
        return ""
    return f"{days} {plural(days, 'Day', 'Days')} / {nights} {plural(nights, 'Night', 'Nights')}"


def travellers_label(adults, children):
    adults, children = int(adults or 0), int(children or 0)
    text = f"{adults:02d} {plural(adults, 'Adult', 'Adults')}"
    text += f" / {children:02d} {plural(children, 'Child', 'Children')}"
    return text


def auto_destinations(hotels):
    """Unique hotel locations in order: 'Munnar – Thekkady – Vagamon – Varkala'."""
    seen, out = set(), []
    for h in hotels:
        loc = (h.location or "").strip()
        if loc and loc.lower() not in seen:
            seen.add(loc.lower())
            out.append(loc)
    return " – ".join(out)


def gst_mode(customer_gstin, company_gstin):
    """Intra-state -> CGST+SGST, inter-state (customer GSTIN from another state) -> IGST."""
    cust = (customer_gstin or "").strip().upper()
    comp = (company_gstin or "").strip().upper()
    if GSTIN_RE.match(cust) and comp[:2].isdigit() and cust[:2] != comp[:2]:
        return "igst"
    return "cgst_sgst"


def payment(amount, advance, gst_enabled, customer_gstin="", company_gstin=""):
    amount = q2(amount or 0)
    advance = q2(advance or 0)
    cgst = sgst = igst = ZERO
    mode = None
    if gst_enabled:
        mode = gst_mode(customer_gstin, company_gstin)
        if mode == "igst":
            igst = q2(amount * IGST_RATE / 100)
        else:
            cgst = q2(amount * CGST_RATE / 100)
            sgst = q2(amount * SGST_RATE / 100)
    tax = cgst + sgst + igst
    total = amount + tax
    balance = total - advance
    if total > 0 and balance <= 0:
        status = STATUS_PAID
    elif advance > 0:
        status = STATUS_ADVANCE
    else:
        status = STATUS_PENDING
    return {
        "amount": amount,
        "gst_enabled": bool(gst_enabled),
        "mode": mode,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "tax": tax,
        "total": total,
        "advance": advance,
        "balance": balance,
        "status": status,
    }
