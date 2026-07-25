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

## Autonomous layer (no userbot)
VYBLA runs itself through the **Bot API** — the bot is an admin of a channel and a
group and does everything from there. There is deliberately **no Telethon userbot /
user-account automation**: automating a personal account (auto-creating channels,
looped promo posting, mass link-dropping) violates Telegram ToS and is the #1 cause
of permanent account bans — the exact outcome we must avoid. So the one action a bot
can't do (creating the channel/group) is a 5-minute manual step; everything after is
automatic.

**One-time setup:**
1. Run the updated `supabase.sql` (adds the `system` table).
2. Create a **channel** (e.g. "VYBLA — честные вайбы") and a **supergroup**
   ("VYBLA CHAT 💬").
3. Add **@vyblabot** as **admin** to both (channel: post messages; group: delete
   messages + the rest). The bot auto-captures both ids via `my_chat_member` and
   stores them in `system` — check for the "✅ Привязан …" DM to your `ADMIN_ID`.
4. In @BotFather → `/setprivacy` → **Disable** (so the bot sees all group messages
   to moderate; being admin also grants this).

**Then, autonomously:**
- every `AUTOPOST_MINUTES` (default 30): posts a random anonymized vibe to the channel;
- every `TOP_MINUTES` (default 60): posts a Top-3 leaderboard to the group;
- moderates the group: deletes foreign links/@handles always, and (if `GROUP_STRICT=1`)
  any non-VYBLA-link message, with a self-deleting warning.

**Free-tier note:** the scheduler runs in-process, so keep the cron-job.org pinger
hitting `/` every 10 min — it both prevents Render's idle spin-down and keeps the
loops alive. `GROUP_STRICT=0` relaxes the group to allow normal chat.

## Why no `userbot.py` / `gen_session.py`
These were requested but intentionally omitted: they automate a **user account**,
which gets that account banned. All the autonomy they were meant to provide
(auto-posting, moderation, leaderboard) is delivered above via the bot instead.
Real engagement numbers are used in posts — no fabricated view counts.

## Referral growth (invite 3 → free VYBLA+)
Two link types now exist:
- `?start=CODE` — the normal vibe link (send someone a vibe).
- `?start=ref_CODE` — a direct invite link. Whoever opens it and creates their
  own VYBLA account counts toward `CODE`'s referral total (`REFERRAL_GOAL` in
  `config.py`, default 3). Reward is granted atomically in Postgres
  (`register_referral` in `supabase.sql`) — no race condition on concurrent
  signups.
- The "Create my own link" button shown to a guest right after they send a
  vibe is auto-tagged with the recipient's `ref_` link, so the existing vibe
  flow doubles as a referral funnel with no extra step for anyone.
- Menu button **🎁 Пригласить друзей** shows the user's invite link + progress.

**Migration for existing databases:** run the `users` `alter table` block and
the `register_referral` function from `supabase.sql` (adds `referred_by`,
`referral_count`, `referral_rewarded` columns — safe to re-run, uses
`if not exists` / `or replace`).

## One-tap "reply in story"
The "↩️ Ответить в сторис" button opens a tiny Telegram Mini App
(`/story/{vibe_id}` in `webhook.py`) that calls the native
`Telegram.WebApp.shareToStory()` API: it opens Telegram's own story editor
pre-loaded with the vibe card and a tappable link back to the bot (tagged
with the owner's referral code) — one tap, no manual save-and-post. The
image itself is regenerated on demand at `/card/{vibe_id}.png` (not stored).
Requires a recent **mobile** Telegram client; older/desktop clients get an
in-page fallback with instructions, so nothing breaks for them. The bot link
is also baked into the story caption text itself (not just the link sticker),
so it stays visible even if Telegram restricts `widget_link` for this bot
category.

## Growth content
See [`growth/CONTENT_PLAN.md`](growth/CONTENT_PLAN.md) — 8 ready video scripts
(TikTok/Reels/Shorts), a 2-week posting calendar, and hashtag sets for
launching without an existing audience.
