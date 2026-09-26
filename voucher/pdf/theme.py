import os

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
FONT_DIR = os.path.join(STATIC_DIR, "fonts")
LOGO_PATH = os.path.join(STATIC_DIR, "img", "logo.png")
SIGNATURE_PATH = os.path.join(STATIC_DIR, "img", "signature.png")

# Palette — deep forest green + antique gold on ivory
GREEN = HexColor("#153B31")
GREEN_2 = HexColor("#1E4D40")
GREEN_LINE = HexColor("#2F6153")
GOLD = HexColor("#B08A3E")
GOLD_SOFT = HexColor("#D8C08C")
GOLD_PALE = HexColor("#F4EBD6")
IVORY = HexColor("#FBF8F1")
IVORY_2 = HexColor("#F4EEE1")
LINE = HexColor("#E7DDC9")
INK = HexColor("#1D2925")
MUTED = HexColor("#6E7772")
WHITE = HexColor("#FFFFFF")
RED = HexColor("#9B3B2E")
RED_PALE = HexColor("#F7E6E2")
OK = HexColor("#1F6B47")
OK_PALE = HexColor("#E2F0E7")

PAGE_W, PAGE_H = A4
MARGIN_X = 42
MARGIN_TOP = 46
MARGIN_BOTTOM = 56
CONTENT_W = PAGE_W - 2 * MARGIN_X

FONTS = {
    "Poppins": "Poppins-Regular.ttf",
    "Poppins-Medium": "Poppins-Medium.ttf",
    "Poppins-SemiBold": "Poppins-SemiBold.ttf",
    "Poppins-Bold": "Poppins-Bold.ttf",
    "Playfair": "Playfair-Regular.ttf",
    "Playfair-SemiBold": "Playfair-SemiBold.ttf",
    "Playfair-Bold": "Playfair-Bold.ttf",
    "Playfair-Italic": "Playfair-Italic.ttf",
    "NotoSans": "NotoSans-Regular.ttf",
    "NotoSans-Bold": "NotoSans-Bold.ttf",
    "NotoMath": "NotoSansMath-Regular.ttf",
    "NotoSymbols2": "NotoSansSymbols2-Regular.ttf",
}

# Glyph fallback chain for characters the main fonts don't have (→, ✓, ★ ...)
FALLBACK_FONTS = ("NotoSans", "NotoMath", "NotoSymbols2")

_registered = False


def register_fonts():
    global _registered
    if _registered:
        return
    for name, filename in FONTS.items():
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, filename)))
    # <b>/<i> inside paragraphs
    addMapping("Poppins", 0, 0, "Poppins")
    addMapping("Poppins", 1, 0, "Poppins-SemiBold")
    addMapping("Poppins", 0, 1, "Poppins")
    addMapping("Poppins", 1, 1, "Poppins-SemiBold")
    addMapping("Poppins-Medium", 1, 0, "Poppins-SemiBold")
    addMapping("Playfair", 0, 0, "Playfair")
    addMapping("Playfair", 1, 0, "Playfair-Bold")
    addMapping("Playfair", 0, 1, "Playfair-Italic")
    addMapping("Playfair", 1, 1, "Playfair-Bold")
    _registered = True


def hexstr(color):
    return "#" + color.hexval()[2:]
