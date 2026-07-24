"""Inline keyboards."""
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CopyTextButton,
)

from config import t, link_for, MODES, BOT_USERNAME, PREMIUM_PRICE_STARS


def main_menu(lang: str, code: str, unread: int) -> InlineKeyboardMarkup:
    link = link_for(code)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_my_vibes", n=unread), callback_data="my_vibes:0")],
        [InlineKeyboardButton(text=t(lang, "btn_copy"),
                              copy_text=CopyTextButton(text=link))],
        [InlineKeyboardButton(text=t(lang, "btn_duel"), callback_data="duel")],
        [InlineKeyboardButton(text=t(lang, "btn_feed"), callback_data="feed")],
        [InlineKeyboardButton(text=t(lang, "btn_premium"), callback_data="premium")],
    ])


def guest_modes(lang: str, code: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=f"{m['emoji']} {m[lang if lang in ('ru', 'en') else 'ru']}",
        callback_data=f"mode:{code}:{key}",
    )] for key, m in MODES.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vibe_actions(lang: str, vibe_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_reply_story"), callback_data=f"story:{vibe_id}"),
        InlineKeyboardButton(text=t(lang, "btn_report"), callback_data=f"report:{vibe_id}"),
    ]])


def guest_after_send(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_create_own"),
                             url=f"https://t.me/{BOT_USERNAME}?start=go"),
    ]])


def vibes_pagination(lang: str, page: int, has_next: bool) -> InlineKeyboardMarkup:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text=t(lang, "btn_prev"), callback_data=f"my_vibes:{page-1}"))
    if has_next:
        row.append(InlineKeyboardButton(text=t(lang, "btn_next"), callback_data=f"my_vibes:{page+1}"))
    return InlineKeyboardMarkup(inline_keyboard=[row] if row else [])


def premium_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_buy_premium", stars=PREMIUM_PRICE_STARS),
                             callback_data="buy_premium"),
    ]])
