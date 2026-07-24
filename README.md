# VYBLA 🖤

Anonymous vibe-link Telegram bot (NGL/Sendit style, TikTok-native). Users create
`t.me/vybla_bot?start=CODE`, drop it in their bio, and receive anonymous "vibes"
rendered as 1080×1920 story cards.

## Stack
Python 3.11 · Aiogram 3.7 · FastAPI (webhook) · Supabase Postgres · Redis · Pillow.

## File map
| File | Purpose |
|------|---------|
| `webhook.py` | FastAPI app, sets webhook on startup, feeds updates to aiogram |
| `bot.py` | Dispatcher, FSM, all handlers |
| `db.py` | Supabase access (async wrappers over sync client) |
| `cache.py` | Redis rate limits + 24h report blocks |
| `cards.py` | Pillow story-card generator (12 gradients) |
| `filters.py` | Moderation (no links/@/banned words) |
| `keyboards.py` | Inline keyboards |
| `payments.py` | Telegram Stars (XTR) invoices |
| `config.py` | Env, constants, RU/EN i18n |
| `supabase.sql` | Schema + atomic counter RPCs |

## Setup
1. **Supabase:** run `supabase.sql` in the SQL editor. Copy the project URL and the
   **service_role** key.
2. **Redis:** local or Upstash (`rediss://…`).
3. **Env:** copy `.env.example` → `.env`, fill in values. `.env` is gitignored.
4. **Font (optional but recommended):** drop `Montserrat-Bold.ttf` into `assets/`.
5. **BotFather:** see `botfather.md`.

## Run
```bash
pip install -r requirements.txt
uvicorn webhook:app --host 0.0.0.0 --port 8000
```
On startup the webhook is registered at `{WEBHOOK_URL}/webhook/{BOT_TOKEN}`.
`WEBHOOK_URL` must be a public HTTPS URL (Railway/Replit provide one).

### Deploy (Railway)
- Add the repo, set the env vars from `.env`, expose the web port.
- `Procfile` already runs uvicorn. Set `WEBHOOK_URL` to the generated domain.

## Design / policy notes
- **No fake "reveal who" upsell.** Selling fabricated hints about anonymous senders
  is the practice the FTC fined NGL $5M for, and it triggers refund fraud → account
  bans. Premium sells real value only: all designs, no watermark, stats.
- **Growth is in-product** (share link, duel, feed), not spam automation — the only
  ToS-safe path to scale without getting the bot/creator banned.
- **Safety:** per-link 5-min rate limit, link/@ moderation, report → 24h sender
  block + admin alert, senders stored only as a salted hash (never a real id).

## Anonymity is real
The bot never exposes who sent a vibe and never invents a "hint." `from_hash` is a
one-way salted SHA-256, used only for rate-limiting and report-blocking.
