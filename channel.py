"""Autonomous content: the channel gets a visual card feed, the group gets a
leaderboard plus its own occasional discussion card. Driven by scheduler.py.
All actions go through the Bot API on a channel/group where the bot is an
admin — no user-account automation.

Privacy rule: public posts NEVER include the recipient's avatar or any
identifying info — that would deanonymize who a vibe was sent to. Avatars are
only ever attached to the private card DMed to the owner (see bot.py)."""
import logging
import os
import random

from aiogram import Bot
from aiogram.types import FSInputFile

import db
import binding
import cards
from config import BOT_USERNAME

log = logging.getLogger("vybla.channel")

# Several hooks in rotation so consecutive posts don't read as the same
# template on repeat — that's what made the feed feel robotic.
_CHANNEL_CAPTIONS = [
    "💬 анонимно, без цензуры.\n\nсвоя ссылка → @{bot}",
    "🫣 кто-то только что получил это анонимно.\n\nузнай, что скажут тебе → @{bot}",
    "вот что пишут в VYBLA прямо сейчас 👇\n\n🖤 всего вайбов: {total}\nсвоя ссылка → @{bot}",
    "если бы тебе написали ЭТО анонимно…\n\nузнай → @{bot}",
    "🔥 вайб дня (ну, получаса)\n\nтвоя очередь → @{bot}",
    "не мы придумываем, люди правда так пишут 🖤\n\n→ @{bot}",
]

_SPOTLIGHT_CAPTIONS = [
    "😳 обсуждаем: кто-то получил такой вайб.\n\nставь реакцию, если согласен 👇",
    "вот это поворот.\n\nкак вам? 👇",
    "спалили чей-то вайб (анонимно, не переживайте 🖤).\n\nобсудим?",
    "как думаете, за дело или перебор?\n\n👇",
]


async def _post_card(bot: Bot, chat_id: int, text: str, mode: str, caption: str) -> None:
    # Public content never gets the owner's avatar — anonymity by design.
    path = cards.generate_vibe_card(text, mode, avatar_path=None, watermark=True)
    try:
        await bot.send_photo(chat_id, FSInputFile(path), caption=caption)
    except Exception as e:
        log.warning("card post to %s failed: %s", chat_id, e)
    finally:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


async def autopost_vibe(bot: Bot) -> None:
    cid = binding.channel_id()
    if not cid:
        return  # not bound to a channel yet
    pool = await db.recent_feed(limit=100)
    if not pool:
        return
    vibe = random.choice(pool)
    total = await db.count_all_vibes()
    caption = random.choice(_CHANNEL_CAPTIONS).format(bot=BOT_USERNAME, total=total)
    await _post_card(bot, int(cid), vibe["text"], vibe.get("mode", "custom"), caption)


async def post_group_spotlight(bot: Bot) -> None:
    gid = binding.group_id()
    if not gid:
        return  # not bound to a group yet
    pool = await db.recent_feed(limit=100)
    if not pool:
        return
    vibe = random.choice(pool)
    caption = random.choice(_SPOTLIGHT_CAPTIONS)
    await _post_card(bot, int(gid), vibe["text"], vibe.get("mode", "custom"), caption)


async def post_top(bot: Bot) -> None:
    gid = binding.group_id()
    if not gid:
        return  # not bound to a group yet
    top = await db.get_top_users(limit=3)
    if not top:
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🔥 ТОП за час:", ""]
    for i, u in enumerate(top):
        lines.append(f"{medals[i]} {u['link_code']} — {u.get('total_views', 0)} просмотров")
    lines += ["", f"Хочешь в топ? Создай ссылку в @{BOT_USERNAME} и делись ей 🚀"]
    try:
        await bot.send_message(int(gid), "\n".join(lines))
    except Exception as e:
        log.warning("top post failed: %s", e)
