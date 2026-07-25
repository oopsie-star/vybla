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
- every `AUTOPOST_MINUTES` (default 30): posts a **real vibe card image** (not
  plain text) to the channel, with one of several rotating caption hooks so
  consecutive posts don't look identical;
- every `TOP_MINUTES` (default 60): posts a Top-3 leaderboard to the group;
- every `SPOTLIGHT_MINUTES` (default 120): posts a *different* vibe card to
  the group, framed for reactions/discussion rather than browsing — the
  group and channel deliberately never show the same content at the same
  cadence;
- moderates the group: deletes foreign links/@handles always, and (if `GROUP_STRICT=1`)
  any non-VYBLA-link message, with a self-deleting warning.

Public posts never include the recipient's avatar — only the private DM card
sent to the vibe's owner does. Showing it publicly would deanonymize who a
vibe was sent to.

## Content for people who don't use the bot yet
Recycled vibes and stats only interest people already using the app. To give
the channel/group something worth following on its own, `editorial.py` adds
two content types sourced independently of the vibes table:
- every `EDITORIAL_MINUTES` (default 90): the channel gets a short, real
  psychology/relationship tip — red flags, green flags, honesty-in-anonymity
  research — on-topic for the audience this kind of app naturally attracts;
- every `POLL_MINUTES` (default 180): the group gets a native Telegram poll
  (`send_poll`) people can actually vote in, not just scroll past.

Both pick randomly from a curated bank with a no-immediate-repeat guard.
None of it is a fabricated "anonymous message" — that would be the same kind
of dishonesty ruled out for hints/metrics elsewhere in this project. Extend
the `FACTS` / `POLLS` lists in `editorial.py` to keep the content fresh.

**Free-tier note:** the scheduler runs in-process, so keep the cron-job.org pinger
hitting `/` every 10 min — it both prevents Render's idle spin-down and keeps the
loops alive. `GROUP_STRICT=0` relaxes the group to allow normal chat.

## AI banter in the group (dialogue.py) — and where the line is
Every `DIALOGUE_MINUTES` (default 45) the group gets a short scripted-style
conversation between named characters (10-persona cast, 2-4 per scene) on an
on-brand topic (red flags, honesty, anonymous compliments, …). This exists to
make a brand new group not feel like a ghost town before real users show up.

**Why this is different from a fake community:** it's the single VYBLA bot
account posting one clearly-labeled formatted message ("🎭 X и Y обсуждают:
…") — not multiple accounts pretending to be separate real users having a
live conversation. Telegram already tags every bot-posted message, and the
framing itself reads as authored content (like a mini comic), not as real
people currently chatting. That distinction is the whole reason this version
was buildable and the earlier "simulate real users arguing/dating/fighting"
version wasn't — that one would have deceived new members about the group's
actual activity, the same category of problem as the fake-hints and
fake-metrics decisions elsewhere in this project.

**Two real models, not one talking to itself:** the cast is split into two
groups voiced by two different models (`OPENROUTER_MODEL_FEMALE`, default
`xiaomi/mimo-v2.5`; `OPENROUTER_MODEL_MALE`, default `deepseek/deepseek-v4-flash`
— both verified live against OpenRouter's `/models` endpoint, not assumed).
Every line is a separate API call to that persona's model, seeing the
transcript so far — genuine turn-by-turn generation, not one prompt writing
both sides. `_pick_cast()` always includes at least one persona from each
group, so even a 2-person scene is guaranteed cross-model. Swap models purely
via env vars, no code changes.

**Generation cost note:** turn-by-turn calls mean ~4-7 API calls per dialogue
post instead of 1 — still trivial (~$0.15-0.20/month at the default 45-min
cadence) but worth knowing since it's a real multiplier over a single-call
design.

**Content quality — fixed after real feedback that lines were generic
("banal", no specificity):** the fix was prompting, not the model. Each
persona now has a concrete `quirk` (a specific habit/tic, not just an
adjective — e.g. Artём "explains everything through attachment theory and
childhood, even unprompted") and the system prompt (`_ANTI_CLICHE`)
explicitly bans stock phrases ("доверие — это важно", "главное коммуникация")
with worked bad/good examples. Verified live before/after: generic "доверие
строится на мелочах" → specific "он на первом свидании сказал что все
бывшие психи — красный флаг размером с область"-style lines that actually
use each persona's quirk.

This surfaced a real bug while testing it: `xiaomi/mimo-v2.5` is a reasoning
model whose internal "thinking" burns completion-token budget before writing
the reply, and the longer anti-cliché prompt pushed it over — confirmed live
(`reasoning_tokens: 364` against a 300-token cap, `finish_reason: "length"`,
`content: None`). It was failing *silently* too: empty content wasn't logged
as a distinct case before, only foreign-script drops and hard errors were —
fixed both: `_MAX_TOKENS` raised to 1500 (confirmed live: 0 empty turns
across 3 test dialogues, vs. 3 empty turns at 900), and empty content now
logs a warning instead of failing silently.

**Resilience — verified, not assumed:** falls back to a curated scripted
bank (`_FALLBACK_DIALOGUES`) when `OPENROUTER_API_KEY` is unset, and any
individual turn that fails (bad key, timeout, empty output) is skipped rather
than aborting the whole conversation; if fewer than 2 lines survive, the
whole thing falls back to the bank. Tested directly: no key → fallback;
invalid key (real live 401s on every turn) → fallback; both produce a valid
≥2-line result, no crash.

**Auto-throttle:** `bot.py`'s group moderator counts real (non-bot) messages
that survive moderation into a rolling Redis window
(`DIALOGUE_ACTIVITY_WINDOW_HOURS`, default 3h). Once that count reaches
`DIALOGUE_ACTIVITY_THRESHOLD` (default 8), `post_dialogue()` skips posting —
verified directly: forcing the counter to 10 suppressed the next post. As the
group becomes genuinely active, the AI banter backs off on its own.

Extend the cast or topics by editing `PERSONAS` / `TOPICS` in `dialogue.py`.

**Presentation — separate typed-out bubbles, not one text block:** each line
posts as its own message, preceded by a real `sendChatAction("typing")`
indicator and a length-proportional delay, so it visually reads as a
conversation happening rather than a pasted transcript. Every persona has a
display avatar emoji + nickname + gender emoji rendered inside the message
text (e.g. "🌙 eva_watches 👩"). **Hard platform limit, not a choice:**
Telegram always shows the actual sender name/avatar/"bot" tag for every
message from the single VYBLA bot account — no per-line formatting can make
Telegram display a different sender identity per character. A ~4-7 line
scene takes roughly 20-80s of wall-clock posting time (background task, not
blocking anything); a live foreign-script leak (see `_FOREIGN_SCRIPT_RE`
above) was caught and correctly dropped during testing of this version too.

## Vibe cards: real variety + a "quote card" design
Two things fixed after real-world feedback that the cards looked bare and
kept repeating the same one test phrase:
- **Design** (`cards.py`): every card now gets a mode badge pill (colored
  accent dot + label — deliberately not an emoji glyph, since plain text
  fonts have no color-emoji glyphs and a headless Linux container usually
  has no emoji font either, which rendered as a blank box when tried) and a
  large decorative quote mark behind the text — the classic "quote card"
  look instead of bare centered text on a gradient.
- **Content variety** (`vibe_examples.py`): ~67 curated example vibe texts
  across all 4 modes, used ONLY when the real `vibes` table has fewer than
  `REAL_POOL_THRESHOLD` (5) entries — i.e. cold start, before real users
  exist. Captions explicitly say "пример"/demo when an example is used
  (`_EXAMPLE_CAPTIONS` in `channel.py`), never claimed as a real submission —
  the same honesty rule as everywhere else in this project. Once real vibes
  accumulate past the threshold, the example bank stops being used entirely.

## Real news (news.py) + interactive quiz (quiz.py)
Added after feedback that AI banter alone still felt thin for a youth
audience. Both are genuine content, not fabricated:

**News** — RSS aggregation posted to the channel as headline + link back to
the source (never full-text reproduction — copyright, and it's honest
attribution instead of pretending to be original content). Sources were
picked by actually curling ~15 candidate RU and US publications and reading
real `<item>` entries, not guessed:
- RU: only `knife.media/feed/` worked (wonderzine, psychologies.ru, mel.fm,
  cosmo.ru, batenka.ru, the-village all 404'd/timed out/served an antibot
  page). It's a general feed, filtered client-side by category relevance.
- US, youth/relationships: `refinery29.com` and `cosmopolitan.com` both have
  real dedicated `/relationships/` RSS feeds — verified genuinely on-topic
  ("invisible string theory", "chronically single for a decade"). Note:
  `bustle.com/rss/relationships` LOOKS like a match by URL but is actually
  celebrity/wedding news underneath — checked and excluded.
- English titles are translated to Russian live via OpenRouter
  (`OPENROUTER_MODEL_TRANSLATE`, defaults to the same deepseek model already
  verified for coherent Russian); translation failure falls back to posting
  the original English title rather than blocking the post — still honest
  content, just less polished. Posted links are deduplicated via a Redis set
  for 30 days so the same story doesn't repeat. Cadence: `NEWS_MINUTES`
  (default 150).

**Quiz** — a real multi-question personality test with a computed result
(`quiz.py` + FSM handlers in `bot.py`), not a single Telegram poll. Tied
directly to VYBLA's own mechanic (how you react to anonymous vibes: Детектив
/ Скептик / Коллекционер / Хаотичное нейтральное) instead of generic
Buzzfeed-style filler, so it reads as on-brand rather than bolted on.
Reachable from the main menu (**🧠 Тест**) and promoted periodically to the
group (`promote_quiz` in `editorial.py`, cadence `QUIZ_PROMO_MINUTES`,
default 240). Scoring picks the most-answered result type, breaking ties
randomly among the tied leaders — verified directly (a genuine 2-2-1 tie
split ~50/50 between the two leaders across 200 runs, the non-tied option
never selected).

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
