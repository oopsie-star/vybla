"""Autonomous content: post anonymized vibes to the channel and a leaderboard
to the group. Driven by scheduler.py. All actions go through the Bot API on a
channel/group where the bot is an admin — no user-account automation."""
import logging
import random

from aiogram import Bot

import db
import binding
from config import BOT_USERNAME

log = logging.getLogger("vybla.channel")


async def autopost_vibe(bot: Bot) -> None:
    cid = binding.channel_id()
    if not cid:
        return  # not bound to a channel yet
    pool = await db.recent_feed(limit=100)
    if not pool:
        return
    vibe = random.choice(pool)
    total = await db.count_all_vibes()  # REAL number, not a fabricated view count
    text = (
        f"💬 «{vibe['text']}»\n\n"
        f"🖤 уже {total} анонимных вайбов в VYBLA\n\n"
        f"Хочешь так же? Создай свою ссылку → @{BOT_USERNAME}"
    )
    try:
        await bot.send_message(int(cid), text)
    except Exception as e:
        log.warning("channel post failed: %s", e)


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
