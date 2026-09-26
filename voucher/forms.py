"""Turns the booking form into validated values (and back) without touching the DB on errors."""
from datetime import date, datetime
from types import SimpleNamespace

from . import calc
from .models import Hotel

TEXT_FIELDS = {
    # name: max length
    "guest_name": 160,
    "contact": 40,
    "package_name": 200,
    "pickup_city": 120,
    "drop_city": 120,
    "destinations": 300,
    "transport": 120,
    "customer_business": 200,
}
LONG_FIELDS = ("itinerary", "inclusions", "exclusions")


def _d(value):
    return value.isoformat() if value else ""


def _amount(value):
    text = f"{value:.2f}"
    return text[:-3] if text.endswith(".00") else text


def _parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _hotel_ns(location="", hotel_name="", room_type="", check_in="", check_out=""):
    return SimpleNamespace(
        location=location, hotel_name=hotel_name, room_type=room_type, check_in=check_in, check_out=check_out
    )


def blank_form(settings):
    return SimpleNamespace(
        guest_name="", contact="+91 ", adults="2", children="0",
        start_date="", end_date="", issued_on=_d(date.today()),
        package_name="", pickup_city="", drop_city="",
        destinations="", transport=settings.get("default_transport", ""),
        itinerary="",
        inclusions=settings.get("default_inclusions", ""),
        exclusions=settings.get("default_exclusions", ""),
        gst_enabled=False, customer_gstin="", customer_business="",
        package_amount="", advance_amount="",
        hotels=[_hotel_ns()],
    )


def form_from_booking(b):
    return SimpleNamespace(
        guest_name=b.guest_name, contact=b.contact, adults=str(b.adults), children=str(b.children),
        start_date=_d(b.start_date), end_date=_d(b.end_date), issued_on=_d(b.issued_on),
        package_name=b.package_name, pickup_city=b.pickup_city, drop_city=b.drop_city,
        destinations=b.destinations, transport=b.transport,
        itinerary=b.itinerary, inclusions=b.inclusions, exclusions=b.exclusions,
        gst_enabled=b.gst_enabled, customer_gstin=b.customer_gstin, customer_business=b.customer_business,
        package_amount=_amount(b.package_amount),
        advance_amount=_amount(b.advance_amount),
        hotels=[
            _hotel_ns(h.location, h.hotel_name, h.room_type, _d(h.check_in), _d(h.check_out)) for h in b.hotels
        ] or [_hotel_ns()],
    )


def form_from_request(req, settings):
    """Returns (form_namespace, parsed_values_dict, errors_list)."""
    f = SimpleNamespace()
    errors = []
    parsed = {}

    for name, limit in TEXT_FIELDS.items():
        value = " ".join((req.form.get(name) or "").split())
        setattr(f, name, value)
        parsed[name] = value[:limit]
    for name in LONG_FIELDS:
        value = (req.form.get(name) or "").replace("\r\n", "\n").strip("\n")
        setattr(f, name, value)
        parsed[name] = value

    if parsed["contact"] in ("+91", "+"):
        parsed["contact"] = ""
    if not parsed["guest_name"]:
        errors.append("Guest / lead traveller name is required.")

    # travellers
    f.adults = (req.form.get("adults") or "").strip()
    f.children = (req.form.get("children") or "").strip()
    for name, minimum in (("adults", 1), ("children", 0)):
        try:
            value = int(getattr(f, name) or 0)
            if value < minimum or value > 999:
                raise ValueError
            parsed[name] = value
        except ValueError:
            errors.append(f"Number of {name} must be a whole number{' of at least 1' if minimum else ''}.")

    # dates
    for name in ("start_date", "end_date", "issued_on"):
        setattr(f, name, (req.form.get(name) or "").strip())
        try:
            parsed[name] = _parse_date(getattr(f, name))
        except ValueError:
            parsed[name] = None
            errors.append(f"{name.replace('_', ' ').capitalize()} is not a valid date.")
    if not parsed.get("start_date") or not parsed.get("end_date"):
        errors.append("Travel start and end dates are required.")
    elif parsed["end_date"] < parsed["start_date"]:
        errors.append("Travel end date cannot be before the start date.")
    if not parsed.get("issued_on"):
        parsed["issued_on"] = date.today()

    # hotels
    cols = [req.form.getlist(k) for k in ("hotel_location", "hotel_name", "hotel_room", "hotel_in", "hotel_out")]
    f.hotels, parsed["hotels"] = [], []
    for i, row in enumerate(zip(*cols), start=1):
        location, hotel_name, room, cin, cout = (" ".join((v or "").split()) for v in row)
        if not any((location, hotel_name, room, cin, cout)):
            continue
        f.hotels.append(_hotel_ns(location, hotel_name, room, cin, cout))
        try:
            d_in, d_out = _parse_date(cin), _parse_date(cout)
        except ValueError:
            errors.append(f"Hotel row {i}: invalid date.")
            continue
        if not hotel_name:
            errors.append(f"Hotel row {i}: hotel / resort name is required.")
        if d_in and d_out and d_out <= d_in:
            errors.append(f"Hotel row {i}: check-out must be after check-in.")
        parsed["hotels"].append(
            dict(location=location[:120], hotel_name=hotel_name[:200], room_type=room[:120], check_in=d_in, check_out=d_out)
        )
    if not f.hotels:
        f.hotels = [_hotel_ns()]

    # payment
    f.gst_enabled = req.form.get("gst_mode") == "gst"
    parsed["gst_enabled"] = f.gst_enabled
    f.customer_gstin = (req.form.get("customer_gstin") or "").strip().upper().replace(" ", "")
    parsed["customer_gstin"] = f.customer_gstin if f.gst_enabled else ""
    if not f.gst_enabled:
        parsed["customer_business"] = ""
    if parsed["customer_gstin"] and not calc.GSTIN_RE.match(parsed["customer_gstin"]):
        errors.append("Customer GSTIN should be 15 characters, e.g. 32ABCDE1234F1Z5.")

    for name, label in (("package_amount", "Total package amount"), ("advance_amount", "Advance received")):
        setattr(f, name, (req.form.get(name) or "").strip())
        try:
            parsed[name] = calc.parse_money(getattr(f, name))
        except ValueError:
            parsed[name] = calc.ZERO
            errors.append(f"{label} must be a number.")
    pay = calc.payment(
        parsed["package_amount"], parsed["advance_amount"], parsed["gst_enabled"],
        parsed["customer_gstin"], settings.get("company_gstin", ""),
    )
    if pay["balance"] < 0:
        errors.append(f"Advance received ({calc.inr(pay['advance'])}) is more than the total ({calc.inr(pay['total'])}).")

    return f, parsed, errors


def apply_form(booking, parsed):
    for name in list(TEXT_FIELDS) + list(LONG_FIELDS) + [
        "adults", "children", "start_date", "end_date", "issued_on",
        "gst_enabled", "customer_gstin", "package_amount", "advance_amount",
    ]:
        setattr(booking, name, parsed[name])
    booking.hotels.clear()
    for pos, h in enumerate(parsed["hotels"]):
        booking.hotels.append(Hotel(position=pos, **h))
