"""Paragraph markup that survives anything pasted from WhatsApp/Docs: emojis become Twemoji
images, and characters missing from the main font fall back to Noto fonts."""
import os
import re
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from xml.sax.saxutils import escape

from reportlab.pdfbase import pdfmetrics

from .theme import FALLBACK_FONTS, STATIC_DIR

TWEMOJI_URL = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@15.1.0/assets/72x72/{}.png"
BUNDLED_EMOJI_DIR = os.path.join(STATIC_DIR, "emoji")

_BASE = (
    "\U0001F000-\U0001FAFF"
    "⌀-⏿"
    "①-⓿"
    "■-➿"
    "⤀-⥿"
    "⬀-⯿"
    "〰〽㊗㊙"
)
_SKIN = "\U0001F3FB-\U0001F3FF"
EMOJI_RE = re.compile(
    "(?:[\U0001F1E6-\U0001F1FF]{2})"                       # flags
    "|(?:[0-9#*]️?⃣)"                             # keycaps
    "|(?:"
    f"(?:[{_BASE}]|[©®‼⁉™ℹ↔-↙↩↪]️)"
    f"️?[{_SKIN}]?"
    f"(?:‍[{_BASE}♀♂⚕⚖✈]️?[{_SKIN}]?)*"  # ZWJ sequences
    ")"
)
_INVISIBLE = {"‍", "️", "︎", "⃣"}


def _cache_dir():
    try:
        os.makedirs(BUNDLED_EMOJI_DIR, exist_ok=True)
        if os.access(BUNDLED_EMOJI_DIR, os.W_OK):
            return BUNDLED_EMOJI_DIR  # local dev: fetched emojis get committed with the project
    except OSError:
        pass
    path = os.path.join(tempfile.gettempdir(), "twemoji")  # Vercel: only /tmp is writable
    os.makedirs(path, exist_ok=True)
    return path


def emoji_code(seq):
    cps = [ord(c) for c in seq]
    if 0x200D not in cps:
        cps = [c for c in cps if c != 0xFE0F]
    return "-".join(f"{c:x}" for c in cps)


def _emoji_file(code):
    for folder in (BUNDLED_EMOJI_DIR, _cache_dir()):
        path = os.path.join(folder, code + ".png")
        if os.path.exists(path):
            return path
    return None


def _is_missing(code):
    return os.path.exists(os.path.join(_cache_dir(), code + ".missing"))


def _fetch(code):
    folder = _cache_dir()
    try:
        req = urllib.request.Request(TWEMOJI_URL.format(code), headers={"User-Agent": "voucher-pdf/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
        if not data.startswith(b"\x89PNG"):
            return
        tmp = os.path.join(folder, f".{code}.{os.getpid()}.tmp")
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, os.path.join(folder, code + ".png"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:  # not an emoji Twemoji draws — remember, fall back to a font glyph
            open(os.path.join(folder, code + ".missing"), "w").close()
    except Exception:
        pass  # offline / timeout: render with font fallback this time, retry next time


def prefetch_emoji(texts):
    codes = set()
    for text in texts:
        for m in EMOJI_RE.finditer(text or ""):
            code = emoji_code(m.group(0))
            if not _emoji_file(code) and not _is_missing(code):
                codes.add(code)
    if codes:
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(_fetch, codes))


_cmaps = {}


def _cmap(font):
    if font not in _cmaps:
        _cmaps[font] = pdfmetrics.getFont(font).face.charToGlyph
    return _cmaps[font]


def _text_markup(text, font):
    base = _cmap(font)
    out, buf, current = [], [], None

    def flush():
        if buf:
            chunk = escape("".join(buf))
            out.append(chunk if current is None else f'<font name="{current}">{chunk}</font>')
            buf.clear()

    for ch in text:
        o = ord(ch)
        if ch in _INVISIBLE or 0x1F3FB <= o <= 0x1F3FF:
            continue
        if ch == "\t":
            ch, o = " ", 32
        if o in base or ch == "\n":
            target = None
        else:
            target = next((fb for fb in FALLBACK_FONTS if o in _cmap(fb)), "")
            if target == "":
                continue  # nothing can draw it — drop rather than print a black box
        if target != current:
            flush()
            current = target
        buf.append(ch)
    flush()
    return "".join(out)


def rich(text, font, size):
    """Escape `text` for a reportlab Paragraph whose style uses `font` at `size`."""
    text = text or ""
    out, pos = [], 0
    for m in EMOJI_RE.finditer(text):
        out.append(_text_markup(text[pos:m.start()], font))
        seq = m.group(0)
        path = _emoji_file(emoji_code(seq))
        if path:
            s = size * 1.08
            src = path.replace("\\", "/")
            out.append(f'<img src="{src}" width="{s:.2f}" height="{s:.2f}" valign="{-size * 0.18:.2f}"/>')
        else:
            out.append(_text_markup(seq, font))
        pos = m.end()
    out.append(_text_markup(text[pos:], font))
    return "".join(out)


def starts_with_emoji(text):
    m = EMOJI_RE.match(text or "")
    return m is not None


def strip_emoji(text):
    return EMOJI_RE.sub("", text or "")
