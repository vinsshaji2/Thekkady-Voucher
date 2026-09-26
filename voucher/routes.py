import csv
import io
import re
from datetime import date

from flask import (
    Blueprint, Response, abort, flash, redirect, render_template, request, url_for,
)
from sqlalchemy import or_

from . import calc
from .extensions import db
from .forms import apply_form, blank_form, form_from_booking, form_from_request
from .models import Booking, Hotel
from .settings import FIELDS as SETTING_FIELDS, get_settings, save_settings

bp = Blueprint("main", __name__)

PER_PAGE = 25


def _get_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        abort(404)
    return booking


# ---------------------------------------------------------------- dashboard
@bp.route("/")
def dashboard():
    S = get_settings()
    q = request.args.get("q", "").strip()
    query = Booking.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Booking.guest_name.ilike(like), Booking.code.ilike(like),
            Booking.contact.ilike(like), Booking.package_name.ilike(like),
        ))
    page = db.paginate(query.order_by(Booking.created_at.desc()), per_page=PER_PAGE, error_out=False)

    rows = db.session.query(
        Booking.package_amount, Booking.advance_amount, Booking.gst_enabled,
        Booking.customer_gstin, Booking.start_date,
    ).all()
    today = date.today()
    stats = {"count": len(rows), "upcoming": 0, "value": calc.ZERO, "outstanding": calc.ZERO}
    for amount, advance, gst, gstin, start in rows:
        pay = calc.payment(amount, advance, gst, gstin, S["company_gstin"])
        stats["value"] += pay["total"]
        stats["outstanding"] += max(pay["balance"], calc.ZERO)
        if start and start >= today:
            stats["upcoming"] += 1
    return render_template("dashboard.html", page=page, q=q, stats=stats, today=today)


# ---------------------------------------------------------------- create / edit
@bp.route("/bookings/new", methods=["GET", "POST"])
def booking_new():
    S = get_settings()
    if request.method == "POST":
        f, parsed, errors = form_from_request(request, S)
        if not errors:
            booking = Booking(code=Booking.new_code(S["booking_prefix"]))
            apply_form(booking, parsed)
            db.session.add(booking)
            db.session.commit()
            flash(f"Booking {booking.code} created.", "success")
            return _after_save(booking)
        return render_template("form.html", f=f, errors=errors, booking=None), 422
    return render_template("form.html", f=blank_form(S), errors=[], booking=None)


@bp.route("/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
def booking_edit(booking_id):
    S = get_settings()
    booking = _get_booking(booking_id)
    if request.method == "POST":
        f, parsed, errors = form_from_request(request, S)
        if not errors:
            apply_form(booking, parsed)
            db.session.commit()
            flash(f"Booking {booking.code} updated.", "success")
            return _after_save(booking)
        return render_template("form.html", f=f, errors=errors, booking=booking), 422
    return render_template("form.html", f=form_from_booking(booking), errors=[], booking=booking)


def _after_save(booking):
    if request.form.get("action") == "save_download":
        return redirect(url_for("main.booking_view", booking_id=booking.id, download=1))
    return redirect(url_for("main.booking_view", booking_id=booking.id))


@bp.route("/bookings/<int:booking_id>")
def booking_view(booking_id):
    booking = _get_booking(booking_id)
    return render_template("view.html", b=booking, pay=booking.payment(get_settings()["company_gstin"]))


@bp.route("/bookings/<int:booking_id>/duplicate", methods=["POST"])
def booking_duplicate(booking_id):
    S = get_settings()
    src = _get_booking(booking_id)
    copy = Booking(code=Booking.new_code(S["booking_prefix"]), issued_on=date.today())
    for col in Booking.__table__.columns.keys():
        if col not in ("id", "code", "issued_on", "created_at", "updated_at"):
            setattr(copy, col, getattr(src, col))
    copy.guest_name = f"{src.guest_name} (copy)"[:160]
    for h in src.hotels:
        copy.hotels.append(Hotel(
            position=h.position, location=h.location, hotel_name=h.hotel_name,
            room_type=h.room_type, check_in=h.check_in, check_out=h.check_out,
        ))
    db.session.add(copy)
    db.session.commit()
    flash(f"Duplicated as {copy.code}. Update the guest details below.", "success")
    return redirect(url_for("main.booking_edit", booking_id=copy.id))


@bp.route("/bookings/<int:booking_id>/delete", methods=["POST"])
def booking_delete(booking_id):
    booking = _get_booking(booking_id)
    code = booking.code
    db.session.delete(booking)
    db.session.commit()
    flash(f"Booking {code} deleted.", "info")
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------- PDF
@bp.route("/bookings/<int:booking_id>/pdf")
def booking_pdf(booking_id):
    from .pdf import build_voucher_pdf  # heavy import only when needed

    booking = _get_booking(booking_id)
    pdf = build_voucher_pdf(booking, get_settings())
    guest = re.sub(r"[^A-Za-z0-9]+", "_", booking.guest_name).strip("_") or "Guest"
    filename = f"{booking.code}_{guest}_Booking_Confirmation.pdf"
    disposition = "attachment" if request.args.get("download") else "inline"
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


# ---------------------------------------------------------------- settings & export
@bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        save_settings(request.form)
        flash("Settings saved.", "success")
        return redirect(url_for("main.settings"))
    return render_template("settings.html", fields=SETTING_FIELDS)


@bp.route("/export.csv")
def export_csv():
    S = get_settings()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([
        "Booking ID", "Issued", "Guest", "Adults", "Children", "Contact", "Start", "End", "Package",
        "Pickup", "Drop", "Destinations", "Transport", "Hotels", "GST", "Customer GSTIN",
        "Package Amount", "CGST", "SGST", "IGST", "Total", "Advance", "Balance", "Status",
    ])
    for b in Booking.query.order_by(Booking.created_at.desc()).all():
        p = b.payment(S["company_gstin"])
        hotels = " | ".join(
            f"{h.location}: {h.hotel_name} ({h.check_in or ''} to {h.check_out or ''}, {h.nights}N)" for h in b.hotels
        )
        w.writerow([
            b.code, b.issued_on, b.guest_name, b.adults, b.children, b.contact, b.start_date, b.end_date,
            b.package_name, b.pickup_city, b.drop_city, b.destinations_label, b.transport, hotels,
            "Yes" if b.gst_enabled else "No", b.customer_gstin,
            p["amount"], p["cgst"], p["sgst"], p["igst"], p["total"], p["advance"], p["balance"], p["status"],
        ])
    return Response(
        "﻿" + out.getvalue(),  # BOM so Excel reads ₹/UTF-8 correctly
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="bookings_{date.today():%Y%m%d}.csv"'},
    )


@bp.app_errorhandler(404)
def not_found(_e):
    return render_template("error.html", title="Not found", message="That booking doesn't exist."), 404


@bp.app_errorhandler(400)
def bad_request(e):
    return render_template("error.html", title="Request rejected", message=e.description), 400
