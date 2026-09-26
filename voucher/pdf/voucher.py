"""Builds the Package Confirmation Voucher PDF for one booking."""
import os
import re
from functools import lru_cache
from io import BytesIO

from PIL import Image as PILImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageTemplate, Paragraph, Spacer, Table,
    TableStyle,
)
from reportlab.platypus.flowables import BalancedColumns

from .. import calc
from .flowables import BarBox, Ornament, Pill, SectionHeader, SpacedText
from .richtext import prefetch_emoji, rich, starts_with_emoji, strip_emoji
from .theme import (
    CONTENT_W, GOLD, GOLD_PALE, GOLD_SOFT, GREEN, GREEN_2, GREEN_LINE, INK, IVORY, IVORY_2, LINE,
    LOGO_PATH, MARGIN_BOTTOM, MARGIN_TOP, MARGIN_X, MUTED, OK, OK_PALE, PAGE_H, PAGE_W, RED,
    RED_PALE, SIGNATURE_PATH, WHITE, hexstr, register_fonts,
)

COL_GAP = 26
BODY_H = PAGE_H - MARGIN_TOP - MARGIN_BOTTOM


# ------------------------------------------------------------------ styles
def _styles():
    s = {}
    s["body"] = ParagraphStyle("body", fontName="Poppins", fontSize=9, leading=13.2, textColor=INK)
    s["value"] = ParagraphStyle("value", fontName="Poppins-Medium", fontSize=10, leading=13.5, textColor=INK)
    s["title"] = ParagraphStyle("title", fontName="Playfair-Bold", fontSize=24, leading=28,
                                textColor=GREEN, alignment=TA_CENTER)
    s["subtitle"] = ParagraphStyle("subtitle", fontName="Playfair-Italic", fontSize=11.5, leading=15,
                                   textColor=GOLD, alignment=TA_CENTER)
    s["small_center"] = ParagraphStyle("small_center", fontName="Poppins", fontSize=7.6, leading=10,
                                       textColor=MUTED, alignment=TA_CENTER)
    s["band_value"] = ParagraphStyle("band_value", fontName="Poppins-SemiBold", fontSize=9.4, leading=12.6,
                                     textColor=WHITE)
    s["th"] = ParagraphStyle("th", fontName="Poppins-SemiBold", fontSize=6.9, leading=9, textColor=WHITE)
    s["td"] = ParagraphStyle("td", fontName="Poppins", fontSize=9, leading=12, textColor=INK)
    s["td_strong"] = ParagraphStyle("td_strong", parent=s["td"], fontName="Poppins-SemiBold")
    s["td_small"] = ParagraphStyle("td_small", parent=s["td"], fontSize=7.4, leading=9.5, textColor=MUTED)
    s["td_center"] = ParagraphStyle("td_center", parent=s["td"], alignment=TA_CENTER)
    s["nights"] = ParagraphStyle("nights", fontName="Poppins-SemiBold", fontSize=10, leading=13,
                                 textColor=GREEN, alignment=TA_CENTER)
    s["itin_title"] = ParagraphStyle("itin_title", fontName="Playfair-Bold", fontSize=16, leading=20,
                                     textColor=GREEN, alignment=TA_CENTER)
    s["day"] = ParagraphStyle("day", fontName="Poppins-SemiBold", fontSize=9.2, leading=12.6, textColor=GREEN)
    s["day_sub"] = ParagraphStyle("day_sub", fontName="Playfair-Italic", fontSize=9.6, leading=12.5,
                                  textColor=GOLD, spaceBefore=3, spaceAfter=1)
    s["itin_caps"] = ParagraphStyle("itin_caps", fontName="Poppins-SemiBold", fontSize=8.2, leading=11.5,
                                    textColor=GOLD, spaceBefore=5, spaceAfter=1)
    s["itin"] = ParagraphStyle("itin", fontName="Poppins", fontSize=8.9, leading=13, textColor=INK)
    s["item"] = ParagraphStyle("item", fontName="Poppins", fontSize=8.9, leading=12.8, textColor=INK,
                               spaceAfter=2.2)
    s["item_bullet"] = ParagraphStyle("item_bullet", parent=s["item"], leftIndent=11, bulletIndent=0,
                                      bulletFontName="Poppins-Bold", bulletColor=GOLD)
    s["card_head"] = ParagraphStyle("card_head", fontName="Poppins-SemiBold", fontSize=8.6, leading=11,
                                    textColor=GREEN)
    s["pay_label"] = ParagraphStyle("pay_label", fontName="Poppins", fontSize=9, leading=12, textColor=INK)
    s["pay_amt"] = ParagraphStyle("pay_amt", fontName="Poppins-Medium", fontSize=9.4, leading=12,
                                  textColor=INK, alignment=TA_RIGHT)
    s["pay_label_b"] = ParagraphStyle("pay_label_b", parent=s["pay_label"], fontName="Poppins-SemiBold",
                                      textColor=GREEN)
    s["pay_amt_b"] = ParagraphStyle("pay_amt_b", parent=s["pay_amt"], fontName="Poppins-SemiBold",
                                    fontSize=10.4, textColor=GREEN)
    s["pay_note"] = ParagraphStyle("pay_note", fontName="Poppins", fontSize=7.2, leading=10, textColor=MUTED)
    s["balance"] = ParagraphStyle("balance", fontName="Playfair-Bold", fontSize=23, leading=27,
                                  textColor=WHITE, alignment=TA_CENTER)
    s["balance_note"] = ParagraphStyle("balance_note", fontName="Poppins", fontSize=7.4, leading=10,
                                       textColor=GOLD_SOFT, alignment=TA_CENTER)
    s["term"] = ParagraphStyle("term", fontName="Poppins", fontSize=8, leading=11.4, textColor=MUTED,
                               leftIndent=18, bulletIndent=0, bulletFontName="Poppins-Medium",
                               bulletFontSize=7.4, bulletColor=GOLD, spaceAfter=2)
    s["foot_name"] = ParagraphStyle("foot_name", fontName="Playfair-Bold", fontSize=13, leading=16,
                                    textColor=GREEN)
    s["foot_line"] = ParagraphStyle("foot_line", fontName="Poppins", fontSize=8.2, leading=12.4, textColor=INK)
    s["sig_name"] = ParagraphStyle("sig_name", fontName="Poppins-SemiBold", fontSize=9.4, leading=12,
                                   textColor=INK, alignment=TA_RIGHT)
    s["sig_role"] = ParagraphStyle("sig_role", fontName="Poppins", fontSize=7.4, leading=10,
                                   textColor=MUTED, alignment=TA_RIGHT)
    s["thanks"] = ParagraphStyle("thanks", fontName="Playfair-Italic", fontSize=10.5, leading=14,
                                 textColor=GOLD, alignment=TA_CENTER)
    return s


def P(text, style):
    return Paragraph(rich(text, style.fontName, style.fontSize), style)


def fmt_date(d, pattern="%d %b %Y"):
    return d.strftime(pattern) if d else "—"


def image_flowable(path, max_w, max_h, align="CENTER"):
    if not os.path.exists(path):
        return None
    try:
        with PILImage.open(path) as im:
            w, h = im.size
    except Exception:
        return None
    scale = min(max_w / w, max_h / h)
    img = Image(path, width=w * scale, height=h * scale)
    img.hAlign = align
    return img


@lru_cache(maxsize=4)
def _watermark(path, mtime):
    """Logo faded to ~5% so it sits quietly behind the content."""
    with PILImage.open(path) as im:
        im = im.convert("RGBA")
        white = PILImage.new("RGBA", im.size, (255, 255, 255, 255))
        flat = PILImage.alpha_composite(white, im).convert("RGB")
        faded = PILImage.blend(PILImage.new("RGB", im.size, (255, 255, 255)), flat, 0.04)
    return faded


def watermark_reader():
    if not os.path.exists(LOGO_PATH):
        return None
    try:
        return ImageReader(_watermark(LOGO_PATH, os.path.getmtime(LOGO_PATH)))
    except Exception:
        return None


# ------------------------------------------------------------------ page furniture
def make_canvas(footer_left, footer_mid):
    class NumberedCanvas(rl_canvas.Canvas):
        """Two-pass canvas so every page can say 'Page x of y'."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                self._footer(total)
                super().showPage()
            super().save()

        def _footer(self, total):
            self.saveState()
            self.setStrokeColor(GOLD_SOFT)
            self.setLineWidth(0.6)
            self.line(MARGIN_X, 38, PAGE_W - MARGIN_X, 38)
            t = self.beginText(MARGIN_X, 25)
            t.setFont("Poppins-Medium", 6.6)
            t.setCharSpace(1.2)
            t.setFillColor(MUTED)
            t.textOut(footer_left)
            self.drawText(t)
            self.setFont("Poppins", 6.8)
            self.setFillColor(MUTED)
            self.drawCentredString(PAGE_W / 2, 25, footer_mid)
            self.drawRightString(PAGE_W - MARGIN_X, 25, f"Page {self._pageNumber} of {total}")
            self.restoreState()

    return NumberedCanvas


class VoucherDoc(BaseDocTemplate):
    def __init__(self, buf, title, author):
        super().__init__(
            buf, pagesize=(PAGE_W, PAGE_H), leftMargin=MARGIN_X, rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM, title=title, author=author,
            subject="Package Confirmation Voucher", creator=author,
        )
        self.watermark = watermark_reader()
        body = Frame(MARGIN_X, MARGIN_BOTTOM, CONTENT_W, BODY_H, id="body",
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate("body", [body], onPage=self._page)])

    def _page(self, c, doc):
        c.saveState()
        c.setFillColor(GREEN)
        c.rect(0, PAGE_H - 12, PAGE_W, 12, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(0, PAGE_H - 14, PAGE_W, 2, stroke=0, fill=1)
        if self.watermark and doc.page > 1:  # page 1 is dense; keep it clean
            size = 300
            c.drawImage(self.watermark, (PAGE_W - size) / 2, (PAGE_H - size) / 2 - 20, size, size)
        c.restoreState()


# ------------------------------------------------------------------ sections
def _card_table(rows, col_widths, style_cmds, radius=6):
    t = Table(rows, colWidths=col_widths, cornerRadii=[radius] * 4)
    t.setStyle(TableStyle(style_cmds))
    return t


def _label(text, color=MUTED, size=6.5, space=1.2):
    return SpacedText(text.upper(), "Poppins-Medium", size, color, space=space, height=size * 1.7)


def header_block(b, S, st):
    out = []
    logo = image_flowable(LOGO_PATH, 150, 64)
    if logo:
        out += [logo, Spacer(1, 3)]
    out.append(SpacedText(S["company_name"].upper(), "Playfair-Bold", 19, GREEN, space=2.4, align="CENTER",
                          height=25))
    if S.get("tagline"):
        out.append(SpacedText(S["tagline"].upper(), "Poppins-Medium", 6.8, GOLD, space=3.2, align="CENTER",
                              height=12))
    if S.get("company_gstin"):
        out.append(Paragraph(
            f'GSTIN&nbsp;&nbsp;<font name="Poppins-SemiBold" color="{hexstr(INK)}">{S["company_gstin"]}</font>',
            st["small_center"]))
    out += [Spacer(1, 5), Ornament(210), Spacer(1, 10)]

    # status strip
    status = [Pill("BOOKING CONFIRMED", WHITE, GREEN, dot=GOLD_SOFT)]
    bid = [_label("Booking ID"), Paragraph(b.code, st["td_strong"])]
    issued = [_label("Issued On"), Paragraph(fmt_date(b.issued_on), st["td_strong"])]
    trip = [_label("Trip Starts"), Paragraph(fmt_date(b.start_date), st["td_strong"])]
    w = CONTENT_W
    out.append(_card_table(
        [[status, bid, issued, trip]], [w * 0.34, w * 0.22, w * 0.22, w * 0.22],
        [
            ("BACKGROUND", (0, 0), (-1, -1), IVORY_2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 6.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6.5),
            ("LINEBEFORE", (1, 0), (-1, -1), 0.6, LINE),
        ],
    ))
    out += [
        Spacer(1, 14),
        Paragraph("Package Confirmation Voucher", st["title"]),
        P(f"Prepared exclusively for {b.guest_name}", st["subtitle"]),
        Spacer(1, 12),
    ]
    return out


def guest_section(num, b, S, st):
    pickup = b.pickup_city or "—"
    drop = b.drop_city or "—"
    package = b.duration_label
    if b.package_name:
        package = f"{package} – {b.package_name}" if package else b.package_name
    pairs = [
        ("Guest / Lead Traveller", b.guest_name), ("No. of Travellers", b.travellers_label),
        ("Travel Dates", f"{fmt_date(b.start_date)}  –  {fmt_date(b.end_date)}"), ("Package", package or "—"),
        ("Pickup / Drop", f"{pickup}  →  {drop}"), ("Contact", b.contact or "—"),
    ]
    if b.gst_enabled and (b.customer_gstin or b.customer_business):
        pairs += [("Customer GSTIN", b.customer_gstin or "—"), ("Registered Name", b.customer_business or "—")]

    rows = []
    for i in range(0, len(pairs), 2):
        rows.append([[_label(k), Spacer(1, 2), P(v, st["value"])] for k, v in pairs[i:i + 2]])
    t = _card_table(rows, [CONTENT_W / 2] * 2, [
        ("BACKGROUND", (0, 0), (-1, -1), IVORY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 13),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7.5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.6, LINE),
        ("LINEBEFORE", (1, 0), (1, -1), 0.6, LINE),
    ])
    return [SectionHeader(num, "Guest & Trip Details"), Spacer(1, 5), t, Spacer(1, 13)]


def summary_section(num, b, S, st):
    n_hotels = len(b.hotels)
    if n_hotels:
        stay = f"{n_hotels} {calc.plural(n_hotels, 'Hotel', 'Hotels')} · {b.hotel_nights} " \
               f"{calc.plural(b.hotel_nights, 'Night', 'Nights')}"
    else:
        stay = "As detailed below"
    cells = [
        ("Duration", b.duration_label or "—"),
        ("Destinations", b.destinations_label or "—"),
        ("Stay", stay),
        ("Transport", b.transport or "—"),
    ]
    w = CONTENT_W
    row = [[_label(k, GOLD_SOFT, 6.3, 1.4), Spacer(1, 3), P(v, st["band_value"])] for k, v in cells]
    t = _card_table([row], [w * 0.2, w * 0.38, w * 0.22, w * 0.2], [
        ("BACKGROUND", (0, 0), (-1, -1), GREEN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 13),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 9.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10.5),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.6, GREEN_LINE),
    ], radius=7)
    return [SectionHeader(num, "Package Summary"), Spacer(1, 5), t, Spacer(1, 13)]


def accommodation_section(num, b, S, st):
    if not b.hotels:
        return []
    widths = [26, 88, CONTENT_W - 26 - 88 - 74 - 74 - 50, 74, 74, 50]
    head = [Paragraph(h, st["th"]) for h in ("#", "LOCATION", "HOTEL / RESORT", "CHECK-IN", "CHECK-OUT")]
    head.append(Paragraph("NIGHTS", ParagraphStyle("thc", parent=st["th"], alignment=TA_CENTER)))
    rows = [head]
    for i, h in enumerate(b.hotels, start=1):
        hotel = [P(h.hotel_name or "—", st["td_strong"])]
        if h.room_type:
            hotel.append(P(h.room_type, st["td_small"]))
        rows.append([
            Paragraph(f"{i:02d}", st["td_small"]),
            P(h.location or "—", st["td"]),
            hotel,
            Paragraph(fmt_date(h.check_in), st["td"]),
            Paragraph(fmt_date(h.check_out), st["td"]),
            Paragraph(f"{h.nights:02d}" if h.nights else "—", st["nights"]),
        ])
    total = b.hotel_nights
    rows.append([
        "", Paragraph("Total", st["td_strong"]), "", "", "",
        Paragraph(f"{total:02d}", ParagraphStyle("tot", parent=st["nights"], textColor=GOLD)),
    ])
    n = len(rows)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 6.5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6.5),
        ("TOPPADDING", (0, 1), (-1, -1), 5.5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6.5),
        ("LINEBELOW", (0, 1), (-1, -3), 0.5, LINE),
        ("BACKGROUND", (0, n - 1), (-1, n - 1), GOLD_PALE),
        ("SPAN", (1, n - 1), (4, n - 1)),
        ("NOSPLIT", (0, n - 2), (-1, n - 1)),  # never leave the Total row alone on a page
    ]
    for r in range(1, n - 1):
        cmds.append(("BACKGROUND", (0, r), (-1, r), WHITE if r % 2 else IVORY))
    t = Table(rows, colWidths=widths, repeatRows=1, cornerRadii=[7] * 4)
    t.setStyle(TableStyle(cmds))
    return [SectionHeader(num, "Accommodation Details"), Spacer(1, 5), t, Spacer(1, 18)]


DAY_RE = re.compile(r"^day\s*\d+\b", re.I)


def itinerary_flowables(text, st):
    out = []
    prev_day = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            out.append(Spacer(1, 5))
            prev_day = False
            continue
        core = strip_emoji(line).strip(" -–—•*:\t")
        letters = [ch for ch in core if ch.isalpha()]
        if DAY_RE.match(core):
            out += [Spacer(1, 4), BarBox(P(line, st["day"]), IVORY_2, GOLD), Spacer(1, 2)]
            prev_day = True
            continue
        if prev_day and not starts_with_emoji(line) and len(line) < 70 and not line.endswith("."):
            out.append(P(line, st["day_sub"]))
        elif len(letters) >= 4 and all(ch.isupper() for ch in letters) and len(core) < 70:
            out.append(P(line, st["itin_caps"]))
        else:
            out.append(P(line, st["itin"]))
        prev_day = False
    return out


def _list_items(text, st, color):
    items = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if starts_with_emoji(line):
            items.append(P(line, st["item"]))
        else:
            line = line.lstrip("-*•· ").strip()
            style = ParagraphStyle("b", parent=st["item_bullet"], bulletColor=color)
            items.append(Paragraph(rich(line, style.fontName, style.fontSize), style, bulletText="•"))
    return items


def inclusions_section(num, b, S, st):
    inc = _list_items(b.inclusions, st, OK)
    exc = _list_items(b.exclusions, st, RED)
    if not inc and not exc:
        return []

    def head(symbol, label, color):
        return Paragraph(
            f'<font name="NotoSymbols2" color="{hexstr(color)}">{symbol}</font>&nbsp;&nbsp;{label}',
            ParagraphStyle("h", parent=st["card_head"], textColor=color))

    cards = []
    if inc:
        cards.append(("✔", "INCLUSIONS", OK, OK_PALE, inc))
    if exc:
        cards.append(("✕", "EXCLUSIONS", RED, RED_PALE, exc))

    out = [SectionHeader(num, "Inclusions & Exclusions"), Spacer(1, 7)]
    longest = max(len(c[4]) for c in cards)
    if len(cards) == 2 and longest <= 22:
        cw = (CONTENT_W - 12) / 2
        tables = []
        for symbol, label, color, pale, items in cards:
            tables.append(_card_table([[[head(symbol, label, color), Spacer(1, 7)] + items]], [cw], [
                ("BACKGROUND", (0, 0), (-1, -1), IVORY),
                ("LINEABOVE", (0, 0), (-1, 0), 2, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 13),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
        outer = Table([[tables[0], "", tables[1]]], colWidths=[cw, 12, cw])
        outer.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        out.append(outer)
    else:  # long lists flow freely across pages
        for symbol, label, color, _, items in cards:
            out += [head(symbol, label, color), Spacer(1, 5)] + items + [Spacer(1, 10)]
    out.append(Spacer(1, 18))
    return out


def payment_section(num, b, S, st):
    pay = b.payment(S.get("company_gstin", ""))
    rows, bold_rows = [], []

    def add(label, amount, bold=False, note=""):
        lab = label + (f'&nbsp;&nbsp;<font name="Poppins-SemiBold" size="6.5" color="{hexstr(OK)}">{note}</font>'
                       if note else "")
        rows.append([Paragraph(lab, st["pay_label_b" if bold else "pay_label"]),
                     Paragraph(calc.inr(amount), st["pay_amt_b" if bold else "pay_amt"])])
        if bold:
            bold_rows.append(len(rows) - 1)

    if pay["gst_enabled"]:
        add("Package Value", pay["amount"])
        if pay["mode"] == "igst":
            add("IGST @ 5%", pay["igst"])
        else:
            add("CGST @ 2.5%", pay["cgst"])
            add("SGST @ 2.5%", pay["sgst"])
        add("Total Package Value", pay["total"], bold=True)
    else:
        add("Total Package Value", pay["total"], bold=True)
    add("Advance Received", pay["advance"], note="PAID" if pay["advance"] > 0 else "")
    add("Balance Due", pay["balance"], bold=True)

    left_w = CONTENT_W * 0.6 - 8
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 5.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
        ("BACKGROUND", (0, 0), (-1, -1), IVORY),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINE),
    ]
    for r in bold_rows:
        cmds.append(("BACKGROUND", (0, r), (-1, r), GOLD_PALE))
    items = _card_table(rows, [left_w * 0.62, left_w * 0.38], cmds)

    left = [items]
    notes = []
    if pay["gst_enabled"]:
        tax = "IGST 5%" if pay["mode"] == "igst" else "CGST 2.5% + SGST 2.5%"
        notes.append(f"GST charged: {tax}")
        if S.get("sac_code"):
            notes.append(f"SAC {S['sac_code']}")
        if b.customer_gstin:
            notes.append(f"Customer GSTIN {b.customer_gstin}")
    else:
        notes.append("Amount shown is without GST")
    left += [Spacer(1, 5), Paragraph("  ·  ".join(notes), st["pay_note"])]

    status_colors = {
        calc.STATUS_PAID: (GREEN, GOLD_SOFT),
        calc.STATUS_ADVANCE: (GREEN, GOLD_SOFT),
        calc.STATUS_PENDING: (WHITE, RED),
    }
    fg, bg = status_colors[pay["status"]]
    right_w = CONTENT_W * 0.4 - 8
    balance_label = "BALANCE DUE" if pay["balance"] > 0 else "AMOUNT SETTLED"
    right = _card_table([[[
        SpacedText(balance_label, "Poppins-Medium", 6.8, GOLD_SOFT, space=2.4, align="CENTER", height=12),
        Spacer(1, 5),
        Paragraph(calc.inr(max(pay["balance"], calc.ZERO) if pay["balance"] > 0 else pay["total"]),
                  st["balance"]),
        Spacer(1, 3),
        Paragraph(f"of {calc.inr(pay['total'])} total package value", st["balance_note"]),
        Spacer(1, 11),
        Pill(pay["status"].upper(), fg, bg, align="CENTER"),
    ]]], [right_w], [
        ("BACKGROUND", (0, 0), (-1, -1), GREEN),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
    ], radius=8)

    outer = Table([[left, "", right]], colWidths=[left_w, 16, right_w])
    outer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [KeepTogether([SectionHeader(num, "Payment Summary"), Spacer(1, 7), outer]), Spacer(1, 14)]


def terms_section(num, S, st):
    lines = [ln.strip().lstrip("-*•· ").strip() for ln in (S.get("terms") or "").splitlines() if ln.strip()]
    if not lines:
        return []
    out = [SectionHeader(num, "Important Notes & Terms"), Spacer(1, 6)]
    for i, line in enumerate(lines, start=1):
        out.append(Paragraph(rich(line, "Poppins", 8), st["term"], bulletText=f"{i:02d}"))
    out.append(Spacer(1, 12))
    return out


def footer_block(S, st):
    lines = []
    for key, label in (("phone", "T"), ("email", "E"), ("website", "W")):
        if S.get(key):
            lines.append(f'<font name="Poppins-SemiBold" color="{hexstr(GOLD)}">{label}</font>&nbsp;&nbsp;&nbsp;'
                         + rich(S[key], "Poppins", 8.2))
    if S.get("address"):
        addr = "<br/>".join(rich(x.strip(), "Poppins", 8.2) for x in S["address"].splitlines() if x.strip())
        lines.append(f'<font name="Poppins-SemiBold" color="{hexstr(GOLD)}">A</font>&nbsp;&nbsp;&nbsp;{addr}')

    left = [P(S["company_name"], st["foot_name"])]
    if S.get("tagline"):
        left.append(_label(S["tagline"], GOLD, 6.3, 2))
    left += [Spacer(1, 6)] + [Paragraph(x, st["foot_line"]) for x in lines]

    right = [SpacedText(f"FOR {S['company_name'].upper()}", "Poppins-Medium", 6.3, MUTED, space=1.3,
                        align="RIGHT", height=11)]
    sig = image_flowable(SIGNATURE_PATH, 120, 40, align="RIGHT")
    right += [Spacer(1, 2), sig] if sig else [Spacer(1, 36)]
    right += [Spacer(1, 3), P(S.get("executive_name", ""), st["sig_name"]),
              Paragraph(f'{S.get("executive_title", "")} · Authorised Signatory', st["sig_role"])]

    w = CONTENT_W
    t = _card_table([[left, right]], [w * 0.58, w * 0.42], [
        ("BACKGROUND", (0, 0), (-1, -1), IVORY_2),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LINEABOVE", (0, 0), (-1, 0), 2, GOLD),
    ], radius=7)
    out = [t]
    if S.get("thank_you"):
        out.append(KeepTogether([Spacer(1, 12), Ornament(120, GOLD_SOFT), Spacer(1, 5),
                                 P(S["thank_you"], st["thanks"])]))
    return out


# ------------------------------------------------------------------ build
def build_voucher_pdf(b, S):
    register_fonts()
    st = _styles()
    prefetch_emoji([b.itinerary, b.inclusions, b.exclusions, S.get("terms"), b.guest_name, b.package_name,
                    b.destinations_label] + [h.hotel_name for h in b.hotels])

    counter = iter(f"{i:02d}" for i in range(1, 20))
    story = header_block(b, S, st)
    story += guest_section(next(counter), b, S, st)
    story += summary_section(next(counter), b, S, st)
    story += accommodation_section(next(counter), b, S, st)

    if b.itinerary.strip():
        num = next(counter)
        heading = b.duration_label
        if b.package_name:
            heading = f"{heading} — {b.package_name}" if heading else b.package_name
        head = SpacedText(f"{num}  ·  DAY-WISE ITINERARY", "Poppins-Medium", 7.2, GOLD, space=2.6,
                          align="CENTER", height=13)
        title = P(heading or "Your Journey", st["itin_title"])
        for f in (head, title):
            f.keepWithNext = 1
        story += [
            CondPageBreak(260), head, Spacer(1, 2), title, Spacer(1, 4), Ornament(170), Spacer(1, 14),
            BalancedColumns(itinerary_flowables(b.itinerary, st), nCols=2, innerPadding=COL_GAP,
                            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
            Spacer(1, 22),
        ]

    story.append(CondPageBreak(220))
    story += inclusions_section(next(counter), b, S, st)
    story += payment_section(next(counter), b, S, st)
    story += terms_section(next(counter), S, st)
    story += footer_block(S, st)

    buf = BytesIO()
    company = S.get("company_name", "")
    doc = VoucherDoc(buf, title=f"{b.code} · {b.guest_name} · Booking Confirmation", author=company)
    footer_left = " · ".join(x for x in (company.upper(), (S.get("tagline") or "").upper()) if x)
    doc.build(story, canvasmaker=make_canvas(footer_left, b.code))
    return buf.getvalue()
