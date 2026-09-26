# Thekkady Adventures — Booking Desk

Flask app that stores bookings (full CRUD) and produces a premium **Package Confirmation Voucher** PDF.

- Guest & trip details → **duration auto** (02 Jan – 07 Jan = 6 Days / 5 Nights)
- Hotels with check-in / check-out → **nights auto**, with a warning if hotel nights ≠ trip nights
- Destinations auto-filled from hotel locations (or type your own)
- Paste the itinerary as-is — emojis render in colour, `DAY 1…` lines become highlighted headings
- Inclusions / exclusions pre-filled from Settings, editable per booking
- **Without GST / With GST**: with GST adds 5% on the package amount — CGST 2.5% + SGST 2.5%
  (or IGST 5% automatically when the customer GSTIN is from another state)
- Advance → **balance and payment status auto**
- Single admin login, CSRF protection, CSV export, duplicate booking

## Run locally

```bash
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:5000 and sign in with `admin` / `admin` (local only — set `ADMIN_PASSWORD` in a
`.env` file to change it; see `.env.example`). Data is stored in `instance/bookings.db` (SQLite).

## Replace logo & signature

- `voucher/static/img/logo.png` — transparent PNG, ≥ 600 px wide
- `voucher/static/img/signature.png` — transparent PNG, ~600 × 250 px

Company name, GSTIN, phone, email, executive name, default inclusions/exclusions and terms are edited on
the **Settings** page (stored in the database — no redeploy needed).

## Deploy to Vercel + Neon (free)

1. Push this folder to a GitHub repository (private recommended).
2. Vercel → **Add New Project** → import the repo. Framework preset: **Other**. No build command.
3. Vercel project → **Storage** → **Create Database** → **Neon** (free plan) → connect to the project.
   This adds `DATABASE_URL` automatically. Tables are created on first request.
4. Vercel project → **Settings → Environment Variables**, add:
   - `SECRET_KEY` — output of `python -c "import secrets; print(secrets.token_hex(32))"`
   - `ADMIN_USERNAME` — e.g. `admin`
   - `ADMIN_PASSWORD` — a strong password
5. Redeploy. Open the site and sign in.

### Neon free plan limits (checked Sep 2026 — see neon.com/pricing)

| Limit | Free plan | What it means for you |
|---|---|---|
| Storage | 0.5 GB per project | ~50,000+ bookings. Not a concern. |
| Compute | 100 CU-hours / month | Scales to zero when idle, so a booking desk uses a small fraction. |
| Scale to zero | After 5 min idle (can't disable) | First request after a quiet period takes ~0.5–1 s longer. |
| Restore history | 6 hours | Accidental deletes can only be undone within 6 h → use **Export CSV** as a regular backup. |
| Egress | 5 GB / month | Plenty. |

If you ever outgrow it, the Launch plan is pay-as-you-go (no monthly minimum).

## Project layout

```
api/index.py          Vercel entry point
run.py                Local dev server
voucher/
  calc.py             All derived numbers (duration, nights, GST, balance, ₹ formatting)
  forms.py            Form parsing + validation
  routes.py           Dashboard, CRUD, PDF, settings, CSV export
  auth.py             Admin login + CSRF
  settings.py         Company details & default texts (DB-backed)
  pdf/voucher.py      PDF layout (ReportLab)
  pdf/richtext.py     Emoji → Twemoji images, font fallback for → ✓ ₹ etc.
  static/fonts        Poppins, Playfair Display, Noto (OFL licensed)
  static/emoji        Cached Twemoji PNGs (new emojis are fetched from jsDelivr on first use)
```

## Credits

Emoji graphics: [Twemoji](https://github.com/jdecked/twemoji), © Twitter / X and contributors, CC-BY 4.0.
Fonts: Poppins, Playfair Display, Noto Sans — SIL Open Font License.
