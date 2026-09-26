"""Small custom flowables for the luxury look (letter-spaced caps, pills, ornaments)."""
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable

from .theme import GOLD, GREEN, LINE


def _spaced_width(text, font, size, space):
    return stringWidth(text, font, size) + space * max(len(text) - 1, 0)


class SpacedText(Flowable):
    """One line of letter-spaced text (Paragraph can't track letters)."""

    def __init__(self, text, font, size, color, space=1.2, align="LEFT", height=None):
        super().__init__()
        self.text, self.font, self.size, self.color = text, font, size, color
        self.space, self.align = space, align
        self.h = height or size * 1.55

    def wrap(self, aw, ah):
        self.aw = aw
        return aw, self.h

    def draw(self):
        w = _spaced_width(self.text, self.font, self.size, self.space)
        x = {"LEFT": 0, "CENTER": (self.aw - w) / 2, "RIGHT": self.aw - w}[self.align]
        t = self.canv.beginText(x, (self.h - self.size * 0.7) / 2)
        t.setFont(self.font, self.size)
        t.setCharSpace(self.space)
        t.setFillColor(self.color)
        t.textOut(self.text)
        self.canv.drawText(t)


class Pill(Flowable):
    def __init__(self, text, fg, bg, font="Poppins-SemiBold", size=6.8, space=1.1, padx=9, pady=4.4,
                 align="LEFT", dot=None):
        super().__init__()
        self.text, self.fg, self.bg, self.font, self.size = text, fg, bg, font, size
        self.space, self.padx, self.pady, self.align, self.dot = space, padx, pady, align, dot

    def wrap(self, aw, ah):
        self.aw = aw
        extra = self.size * 1.3 if self.dot else 0
        self.w = _spaced_width(self.text, self.font, self.size, self.space) + 2 * self.padx + extra
        self.h = self.size + 2 * self.pady
        return aw, self.h

    def draw(self):
        c = self.canv
        x = {"LEFT": 0, "CENTER": (self.aw - self.w) / 2, "RIGHT": self.aw - self.w}[self.align]
        c.setFillColor(self.bg)
        c.roundRect(x, 0, self.w, self.h, self.h / 2, stroke=0, fill=1)
        tx = x + self.padx
        if self.dot:
            c.setFillColor(self.dot)
            c.circle(tx + self.size * 0.35, self.h / 2, self.size * 0.3, stroke=0, fill=1)
            tx += self.size * 1.3
        t = c.beginText(tx, self.pady + self.size * 0.14)
        t.setFont(self.font, self.size)
        t.setCharSpace(self.space)
        t.setFillColor(self.fg)
        t.textOut(self.text)
        c.drawText(t)


class Ornament(Flowable):
    """Gold rule — diamond — gold rule."""

    def __init__(self, width=180, color=GOLD, height=10):
        super().__init__()
        self.w, self.color, self.h = width, color, height

    def wrap(self, aw, ah):
        self.aw = aw
        return aw, self.h

    def draw(self):
        c = self.canv
        cx, y = self.aw / 2, self.h / 2
        c.setStrokeColor(self.color)
        c.setFillColor(self.color)
        c.setLineWidth(0.6)
        c.line(cx - self.w / 2, y, cx - 8, y)
        c.line(cx + 8, y, cx + self.w / 2, y)
        r = 3.1
        p = c.beginPath()
        p.moveTo(cx, y + r)
        p.lineTo(cx + r, y)
        p.lineTo(cx, y - r)
        p.lineTo(cx - r, y)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        c.circle(cx - 12, y, 0.9, stroke=0, fill=1)
        c.circle(cx + 12, y, 0.9, stroke=0, fill=1)


class SectionHeader(Flowable):
    """'03  ACCOMMODATION DETAILS ─────────'"""

    def __init__(self, number, title):
        super().__init__()
        self.number, self.title = number, title.upper()
        self.keepWithNext = 1

    def wrap(self, aw, ah):
        self.aw = aw
        return aw, 22

    def draw(self):
        c = self.canv
        c.setFont("Poppins-Medium", 8.4)
        c.setFillColor(GOLD)
        c.drawString(0, 7.5, self.number)
        x = stringWidth(self.number, "Poppins-Medium", 8.4) + 7
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.8)
        c.line(x, 10.5, x + 10, 10.5)
        x += 17
        t = c.beginText(x, 7.5)
        t.setFont("Poppins-SemiBold", 8.4)
        t.setCharSpace(1.9)
        t.setFillColor(GREEN)
        t.textOut(self.title)
        c.drawText(t)
        end = x + _spaced_width(self.title, "Poppins-SemiBold", 8.4, 1.9) + 12
        c.setStrokeColor(LINE)
        c.setLineWidth(0.7)
        c.line(end, 10.5, self.aw, 10.5)


class BarBox(Flowable):
    """A paragraph on a tinted panel with a gold bar on the left (day headings)."""

    def __init__(self, para, bg, bar, pad=(5.5, 8, 5.5, 10), bar_w=2.4, radius=3):
        super().__init__()
        self.para, self.bg, self.bar, self.pad = para, bg, bar, pad
        self.bar_w, self.radius = bar_w, radius
        self.keepWithNext = 1

    def wrap(self, aw, ah):
        top, right, bottom, left = self.pad
        _, h = self.para.wrap(aw - left - right, ah)
        self.aw, self.h = aw, h + top + bottom
        return aw, self.h

    def draw(self):
        c = self.canv
        top, right, bottom, left = self.pad
        c.setFillColor(self.bg)
        c.roundRect(0, 0, self.aw, self.h, self.radius, stroke=0, fill=1)
        c.setFillColor(self.bar)
        c.rect(0, 0, self.bar_w, self.h, stroke=0, fill=1)
        self.para.drawOn(c, left, bottom)
