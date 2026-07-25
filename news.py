"""Real news aggregation: youth-culture / psychology / relationships content
pulled from RSS, posted to the channel as headline + link back to the
source — never full-text reproduction (copyright), always attributed. This
is real published journalism, not fabricated content, so it needs no
"example" framing the way vibe_examples.py does.

Sources were picked by actually curling ~15 candidate RU and US
publications and checking for real <item> entries, not guessed:
- RU: only knife.media/feed/ worked (wonderzine, psychologies.ru, mel.fm,
  cosmo.ru, batenka.ru, the-village all 404'd, timed out, or served an
  antibot/error page). It's a general feed, so items are filtered by their
  own <category> tags for relevance.
- US, youth/relationships-focused: refinery29.com and cosmopolitan.com both
  have real dedicated /relationships/ RSS feeds (verified: genuinely dating/
  relationship content, e.g. "invisible string theory", "chronically single
  for a decade"). bustle.com/rss/relationships LOOKS like a match by URL but
  is actually celebrity/wedding news under the hood — verified and excluded.
  English items are translated to Russian via OpenRouter before posting.

Add more feeds the same way: curl the URL, read real titles, don't guess.
"""
import logging
import random
import xml.etree.ElementTree as ET

import httpx
from aiogram import Bot

import binding
import cache
from config import BOT_USERNAME, OPENROUTER_API_KEY, OPENROUTER_MODEL_TRANSLATE

log = logging.getLogger("vybla.news")

FEEDS = [
    # Russian, general feed — filtered client-side by category relevance.
    {"url": "https://knife.media/feed/", "lang": "ru", "filter": True},
    # English, already relationship-specific category feeds — no extra
    # filtering needed, but titles need translation before posting.
    {"url": "https://www.refinery29.com/en-us/relationships/rss.xml", "lang": "en", "filter": False},
    {"url": "https://www.cosmopolitan.com/rss/relationships.xml/", "lang": "en", "filter": False},
    # English, general feed (no dedicated category feed exists — verified:
    # /love/, /relationships/, /self/ all 404) — filtered client-side, same
    # as knife.media. Its own <category> tags cleanly separate relevant
    # ("Love", "Dating", "Self") from horoscope filler ("zodiac",
    # "astrology"), which _is_relevant excludes explicitly.
    {"url": "https://www.yourtango.com/rss.xml", "lang": "en", "filter": True},
]

# greatist.com/feed was tested and rejected: it returned real HTTP 200 with
# 50 <item> entries, but they were all sponsor/test placeholders ("noom
# weight epm", "Test sponsor") rather than real articles — a genuinely
# broken feed despite a healthy-looking response. A 200 status and item
# count are not enough to trust a source; the actual titles were checked.

_RELEVANT_KEYWORDS_RU = (
    "психол", "отношен", "любов", "чувств", "секс", "семь", "дружб",
    "свидан", "эмоц", "привязанност", "одиночеств",
)
_RELEVANT_KEYWORDS_EN = (
    "relationship", "dating", "love", "breakup", "marriage", "partner",
    "emotional", "self", "single", "friendship", "attachment", "crush",
)
_EXCLUDE_KEYWORDS_EN = ("zodiac", "astrology", "horoscope")

_POST_TEMPLATES = [
    "📰 {title}\n\nподробнее → {link}\n\nа как у тебя? делись анонимно → @{bot}",
    "🧠 {title}\n\nчитать → {link}\n\nсвоя правда тут → @{bot}",
    "{title}\n\n👉 {link}",
]

_SEEN_KEY = "news_posted_links"
# The combined pool across all feeds is only ~40-70 items at a time (real
# publishers don't produce more than a handful of on-topic pieces per day
# combined) — a 30-day "never repeat" window would exhaust it in well under
# a day at a 15-min check cadence and then go silent. 3 days lets the pool
# recirculate instead, so checks keep finding something to post.
_SEEN_TTL = 3 * 24 * 3600


async def _fetch_items(feed: dict) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(feed["url"])
            resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        log.warning("news feed fetch failed for %s: %s", feed["url"], e)
        return []
    items = []
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        cats = [c.text.lower() for c in it.findall("category") if c.text]
        if title and link:
            items.append({
                "title": title, "link": link, "categories": cats,
                "lang": feed["lang"], "needs_filter": feed["filter"],
            })
    return items


def _is_relevant(item: dict) -> bool:
    if not item["needs_filter"]:
        return True  # already a dedicated relationships-category feed
    haystack = " ".join(item["categories"]) + " " + item["title"].lower()
    if item["lang"] == "en":
        if any(k in haystack for k in _EXCLUDE_KEYWORDS_EN):
            return False
        return any(k in haystack for k in _RELEVANT_KEYWORDS_EN)
    return any(k in haystack for k in _RELEVANT_KEYWORDS_RU)


async def _translate_title(title: str) -> str:
    """Best-effort EN->RU headline translation. Returns the original title
    unchanged on any failure — an untranslated real headline is still honest
    content, just less polished, so this never blocks posting."""
    if not OPENROUTER_API_KEY:
        return title
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_MODEL_TRANSLATE,
                    "messages": [
                        {"role": "system", "content": (
                            "Переведи заголовок статьи на естественный разговорный "
                            "русский. Только перевод, без пояснений и без кавычек."
                        )},
                        {"role": "user", "content": title},
                    ],
                    "max_tokens": 800,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            translated = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning("news title translation failed, posting original: %s", e)
        return title
    translated = (translated or "").strip().strip('"').strip()
    return translated or title


async def post_news(bot: Bot) -> None:
    cid = binding.channel_id()
    if not cid:
        return

    pool: list[dict] = []
    for feed in FEEDS:
        pool.extend(await _fetch_items(feed))
    relevant = [it for it in pool if _is_relevant(it)]
    if not relevant:
        log.info("no relevant news items this round (%d fetched, 0 relevant)", len(pool))
        return

    fresh = []
    for it in relevant:
        seen = await cache.redis.sismember(_SEEN_KEY, it["link"])
        if not seen:
            fresh.append(it)
    if not fresh:
        log.info("all relevant items already posted recently")
        return

    item = random.choice(fresh)
    await cache.redis.sadd(_SEEN_KEY, item["link"])
    await cache.redis.expire(_SEEN_KEY, _SEEN_TTL)

    title = item["title"]
    if item["lang"] == "en":
        title = await _translate_title(title)

    text = random.choice(_POST_TEMPLATES).format(title=title, link=item["link"], bot=BOT_USERNAME)
    try:
        await bot.send_message(int(cid), text)
    except Exception as e:
        log.warning("news post failed: %s", e)
