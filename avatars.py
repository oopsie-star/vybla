"""Shared helper to fetch a Telegram user's avatar as a local temp file.
Used by bot.py (card delivered in chat) and webhook.py (on-demand card
regeneration for the share-to-story mini app)."""
import logging
import os
import tempfile

from aiogram import Bot

log = logging.getLogger("vybla.avatars")


async def download_avatar(bot: Bot, user_id: int) -> str | None:
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if not photos.total_count or not photos.photos:
            return None
        file_id = photos.photos[0][-1].file_id
        tg_file = await bot.get_file(file_id)
        dest = os.path.join(tempfile.gettempdir(), f"av_{user_id}.jpg")
        await bot.download_file(tg_file.file_path, dest)
        return dest
    except Exception as e:  # private avatar, no photo, etc.
        log.info("avatar fetch failed for %s: %s", user_id, e)
        return None
