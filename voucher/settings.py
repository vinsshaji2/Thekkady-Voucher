"""Company details and default texts, editable from the Settings page (stored in the DB)."""
from flask import g

from .extensions import db
from .models import Setting

DEFAULT_INCLUSIONS = """🏨 Accommodation at all properties mentioned above
☕ Breakfast throughout the stay
🚗 Private Sedan for the entire trip
👨‍✈️ Dedicated driver throughout the journey
🌿 Sightseeing as mentioned in the itinerary"""

DEFAULT_EXCLUSIONS = """🎟️ All entry tickets and entrance fees
🍛 All Lunch & Dinner
🪂 Optional activities such as Zipline & Glass Bridge
💳 Personal expenses
🛍️ Shopping and personal purchases
🥤 Snacks, beverages and room-service expenses
🧾 Expenses arising due to unforeseen circumstances
💰 Anything not specifically mentioned under inclusions"""

DEFAULT_TERMS = """This confirmation is valid only for the services and dates mentioned above.
Hotel rooms are subject to the confirmed room category and availability at the time of booking.
Check-in / check-out times follow the respective hotel's policy.
Any changes to the itinerary, hotel, vehicle or activities may affect the package price.
Cancellation and refund terms are governed by the booking terms communicated at the time of confirmation.
Guests are advised to carry valid government-issued ID and any required travel documents."""

# (key, label, default, kind) — kind drives the settings form widget
FIELDS = [
    ("company_name", "Company name", "Thekkady Adventures", "text"),
    ("tagline", "Tagline", "The Travel Makers", "text"),
    ("company_gstin", "Company GSTIN", "32AAWFT9099G1ZB", "text"),
    ("sac_code", "SAC code (tour operator)", "998552", "text"),
    ("phone", "Phone", "+91 88483 21521", "text"),
    ("email", "Email", "infothekkadyadventures@gmail.com", "text"),
    ("website", "Website", "www.thekkadyadventures.com", "text"),
    ("address", "Address (optional)", "", "textarea"),
    ("executive_name", "Booking executive", "Jebin Abraham", "text"),
    ("executive_title", "Executive title", "Booking Executive", "text"),
    ("booking_prefix", "Booking ID prefix", "TA", "text"),
    ("default_transport", "Default transport", "Sedan", "text"),
    ("default_inclusions", "Default inclusions (one per line)", DEFAULT_INCLUSIONS, "textarea"),
    ("default_exclusions", "Default exclusions (one per line)", DEFAULT_EXCLUSIONS, "textarea"),
    ("terms", "Important notes & terms (one per line)", DEFAULT_TERMS, "textarea"),
    (
        "thank_you",
        "Closing line",
        "Thank you for choosing Thekkady Adventures. We look forward to making your Kerala journey memorable.",
        "text",
    ),
]

DEFAULTS = {key: default for key, _, default, _ in FIELDS}


def get_settings():
    if "settings" not in g:
        values = dict(DEFAULTS)
        values.update({row.key: row.value for row in Setting.query.all()})
        g.settings = values
    return g.settings


def save_settings(form):
    for key, _, _, _ in FIELDS:
        value = (form.get(key) or "").replace("\r\n", "\n").strip()
        if key == "company_gstin":
            value = value.upper()
        if key == "booking_prefix":
            value = "".join(ch for ch in value.upper() if ch.isalnum())[:6] or "TA"
        row = db.session.get(Setting, key)
        if row is None:
            db.session.add(Setting(key=key, value=value))
        else:
            row.value = value
    db.session.commit()
    g.pop("settings", None)
