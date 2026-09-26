import secrets
from datetime import date, datetime

from . import calc
from .extensions import db

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I confusion


def _now():
    return datetime.utcnow()


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(24), unique=True, nullable=False, index=True)
    issued_on = db.Column(db.Date, nullable=False, default=date.today)

    guest_name = db.Column(db.String(160), nullable=False)
    adults = db.Column(db.Integer, nullable=False, default=1)
    children = db.Column(db.Integer, nullable=False, default=0)
    contact = db.Column(db.String(40), nullable=False, default="")
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    package_name = db.Column(db.String(200), nullable=False, default="")
    pickup_city = db.Column(db.String(120), nullable=False, default="")
    drop_city = db.Column(db.String(120), nullable=False, default="")

    destinations = db.Column(db.String(300), nullable=False, default="")
    transport = db.Column(db.String(120), nullable=False, default="")

    itinerary = db.Column(db.Text, nullable=False, default="")
    inclusions = db.Column(db.Text, nullable=False, default="")
    exclusions = db.Column(db.Text, nullable=False, default="")

    gst_enabled = db.Column(db.Boolean, nullable=False, default=False)
    customer_gstin = db.Column(db.String(15), nullable=False, default="")
    customer_business = db.Column(db.String(200), nullable=False, default="")
    package_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    advance_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    hotels = db.relationship(
        "Hotel", backref="booking", order_by="Hotel.position", cascade="all, delete-orphan"
    )

    # ---- derived values -------------------------------------------------
    @property
    def days(self):
        return calc.trip_length(self.start_date, self.end_date)[0]

    @property
    def nights(self):
        return calc.trip_length(self.start_date, self.end_date)[1]

    @property
    def duration_label(self):
        return calc.duration_label(self.days, self.nights)

    @property
    def travellers_label(self):
        return calc.travellers_label(self.adults, self.children)

    @property
    def hotel_nights(self):
        return sum(h.nights for h in self.hotels)

    @property
    def destinations_label(self):
        return self.destinations.strip() or calc.auto_destinations(self.hotels)

    def payment(self, company_gstin=""):
        return calc.payment(
            self.package_amount, self.advance_amount, self.gst_enabled, self.customer_gstin, company_gstin
        )

    @staticmethod
    def new_code(prefix="TA"):
        prefix = (prefix or "TA").strip().upper()
        while True:
            code = f"{prefix}-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(7))
            if not Booking.query.filter_by(code=code).first():
                return code


class Hotel(db.Model):
    __tablename__ = "booking_hotels"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    location = db.Column(db.String(120), nullable=False, default="")
    hotel_name = db.Column(db.String(200), nullable=False, default="")
    room_type = db.Column(db.String(120), nullable=False, default="")
    check_in = db.Column(db.Date, nullable=True)
    check_out = db.Column(db.Date, nullable=True)

    @property
    def nights(self):
        if self.check_in and self.check_out and self.check_out > self.check_in:
            return (self.check_out - self.check_in).days
        return 0


class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")
