"""Inline keyboards."""
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CopyTextButton,
    WebAppInfo,
)

from config import t, link_for, MODES, BOT_USERNAME, PREMIUM_PRICE_STARS, WEBHOOK_URL


def main_menu(lang: str, code: str, unread: int) -> InlineKeyboardMarkup:
    link = link_for(code)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_my_vibes", n=unread), callback_data="my_vibes:0")],
        [InlineKeyboardButton(text=t(lang, "btn_copy"),
                              copy_text=CopyTextButton(text=link))],
        [InlineKeyboardButton(text=t(lang, "btn_duel"), callback_data="duel")],
        [InlineKeyboardButton(text=t(lang, "btn_feed"), callback_data="feed")],
        [InlineKeyboardButton(text=t(lang, "btn_invite"), callback_data="invite")],
        [InlineKeyboardButton(text=t(lang, "btn_quiz"), callback_data="quiz_start")],
        [InlineKeyboardButton(text=t(lang, "btn_premium"), callback_data="premium")],
    ])


def guest_modes(lang: str, code: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=f"{m['emoji']} {m[lang if lang in ('ru', 'en') else 'ru']}",
        callback_data=f"mode:{code}:{key}",
    )] for key, m in MODES.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vibe_actions(lang: str, vibe_id: str, owner_code: str) -> InlineKeyboardMarkup:
    # web_app opens Telegram's native share-to-story editor pre-filled with the
    # card + a link back to the bot (see /story and /card routes in webhook.py).
    story_url = f"{WEBHOOK_URL}/story/{vibe_id}?lang={lang}&code={owner_code}"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_reply_story"), web_app=WebAppInfo(url=story_url)),
        InlineKeyboardButton(text=t(lang, "btn_report"), callback_data=f"report:{vibe_id}"),
    ]])


def guest_after_send(lang: str, ref_code: str) -> InlineKeyboardMarkup:
    # Tag this with the vibe recipient's code: if the guest goes on to create
    # their own link, the recipient gets referral credit for growing VYBLA.
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_create_own"),
                             url=f"https://t.me/{BOT_USERNAME}?start=ref_{ref_code}"),
    ]])


def vibes_pagination(lang: str, page: int, has_next: bool) -> InlineKeyboardMarkup:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text=t(lang, "btn_prev"), callback_data=f"my_vibes:{page-1}"))
    if has_next:
        row.append(InlineKeyboardButton(text=t(lang, "btn_next"), callback_data=f"my_vibes:{page+1}"))
    return InlineKeyboardMarkup(inline_keyboard=[row] if row else [])


def quiz_question_kb(q_index: int, options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"quiz:{q_index}:{tag}")]
        for label, tag in options
    ])


def premium_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_buy_premium", stars=PREMIUM_PRICE_STARS),
                             callback_data="buy_premium"),
    ]])
