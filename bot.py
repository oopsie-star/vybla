"""VYBLA bot: dispatcher, FSM, all handlers. Webhook-driven (see webhook.py)."""
import logging
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import (
    Message, CallbackQuery, FSInputFile, BufferedInputFile,
    PreCheckoutQuery,
)

import db
import cards
from cache import (
    redis, sender_hash, allow_guest, guest_locked, is_blocked, block_sender,
)
from filters import moderate
from payments import send_premium_invoice, PREMIUM_PAYLOAD
from keyboards import (
    main_menu, guest_modes, vibe_actions, guest_after_send,
    vibes_pagination, premium_kb,
)
from config import (
    BOT_TOKEN, REDIS_URL, MAX_VIBE_LEN, FEED_SAMPLE, MODES, ADMIN_ID,
    t, lang_of, link_for,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vybla")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(link_preview_is_disabled=True),
)
# Dedicated connection for FSM state (kept separate from the decode_responses
# rate-limit client in cache.py, which aiogram's storage doesn't want).
storage = RedisStorage.from_url(REDIS_URL)
dp = Dispatcher(storage=storage)


class GuestFlow(StatesGroup):
    writing = State()


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
async def _download_avatar(user_id: int) -> str | None:
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if not photos.total_count or not photos.photos:
            return None
        file_id = photos.photos[0][-1].file_id
        tg_file = await bot.get_file(file_id)
        dest = os.path.join(
            os.environ.get("TMPDIR", cards.tempfile.gettempdir()),
            f"av_{user_id}.jpg",
        )
        await bot.download_file(tg_file.file_path, dest)
        return dest
    except Exception as e:  # private avatar, no photo, etc.
        log.info("avatar fetch failed for %s: %s", user_id, e)
        return None


def _mode_label(mode: str, lang: str) -> str:
    m = MODES.get(mode)
    if not m:
        return mode
    return f"{m['emoji']} {m['en'] if lang == 'en' else m['ru']}"


# --------------------------------------------------------------------------
# /start
# --------------------------------------------------------------------------
@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    arg = (command.args or "").strip()

    # Guest flow: arg is a link_code (optionally prefixed with duel_)
    code = arg[5:] if arg.startswith("duel_") else arg
    if code and code not in ("go",) and len(code) <= 12:
        return await _enter_guest_flow(message, code)

    # Owner flow
    await _show_owner_menu(message)


async def _show_owner_menu(message: Message):
    u = message.from_user
    user = await db.get_or_create_user(u.id, u.username, lang_of(u.language_code))
    lang = user["lang"]
    unread = await db.count_unread(user["link_code"])
    await message.answer(
        t(lang, "menu",
          link=link_for(user["link_code"]),
          views=user.get("total_views", 0),
          vibes=user.get("total_vibes", 0)),
        reply_markup=main_menu(lang, user["link_code"], unread),
    )


async def _enter_guest_flow(message: Message, code: str):
    guest = message.from_user
    lang = lang_of(guest.language_code)
    owner = await db.get_user_by_code(code)
    if not owner:
        return await message.answer(t(lang, "broken_link"))

    await db.increment_views(code)

    if await guest_locked(guest.id, code):
        return await message.answer(t(lang, "rate_limited"))

    note = ""
    if owner["id"] == guest.id:
        note = "\n" + t(lang, "self_note")
    owner_name = owner.get("username") or "anon"
    await message.answer(
        t(lang, "ask_mode", owner=owner_name) + note,
        reply_markup=guest_modes(lang, code),
    )


# --------------------------------------------------------------------------
# Guest: mode -> text
# --------------------------------------------------------------------------
@dp.callback_query(F.data.startswith("mode:"))
async def cb_mode(cq: CallbackQuery, state: FSMContext):
    _, code, mode = cq.data.split(":", 2)
    lang = lang_of(cq.from_user.language_code)
    await state.set_state(GuestFlow.writing)
    await state.update_data(to_code=code, mode=mode, guest_lang=lang)
    await cq.message.edit_text(t(lang, "ask_text", n=MAX_VIBE_LEN))
    await cq.answer()


@dp.message(StateFilter(GuestFlow.writing), F.text)
async def guest_write(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("guest_lang", lang_of(message.from_user.language_code))
    code = data["to_code"]
    mode = data.get("mode", "custom")
    text = (message.text or "").strip()

    if len(text) > MAX_VIBE_LEN:
        return await message.answer(t(lang, "too_long", n=MAX_VIBE_LEN))
    ok, reason = moderate(text)
    if not ok:
        return await message.answer(t(lang, reason or "mod_blocked"))

    from_hash = sender_hash(message.from_user.id, code)
    if await is_blocked(from_hash):
        await state.clear()
        return await message.answer(t(lang, "blocked_sender"))
    if not await allow_guest(message.from_user.id, code):
        await state.clear()
        return await message.answer(t(lang, "rate_limited"))

    owner = await db.get_user_by_code(code)
    if not owner:
        await state.clear()
        return await message.answer(t(lang, "broken_link"))

    vibe = await db.add_vibe(code, from_hash, mode, text)
    await db.increment_vibes(code)

    # Build + deliver the card to the OWNER
    avatar = await _download_avatar(owner["id"])
    card_path = cards.generate_vibe_card(
        text, mode, avatar_path=avatar, watermark=not owner.get("is_premium"),
    )
    owner_lang = owner["lang"]
    try:
        await bot.send_photo(
            chat_id=owner["id"],
            photo=FSInputFile(card_path),
            caption=t(owner_lang, "new_vibe_caption", text=text),
            reply_markup=vibe_actions(owner_lang, vibe["id"]),
        )
    except Exception as e:
        log.warning("could not deliver to owner %s: %s", owner["id"], e)
    finally:
        for p in (card_path, avatar):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    await state.clear()
    await message.answer(t(lang, "sent_ok"), reply_markup=guest_after_send(lang))


# --------------------------------------------------------------------------
# Owner: my vibes (paginated text list; the card was already delivered live)
# --------------------------------------------------------------------------
@dp.callback_query(F.data.startswith("my_vibes:"))
async def cb_my_vibes(cq: CallbackQuery):
    page = int(cq.data.split(":")[1])
    user = await db.get_user(cq.from_user.id)
    if not user:
        return await cq.answer()
    lang = user["lang"]
    code = user["link_code"]
    if page == 0:
        await db.mark_read(code)

    rows, has_next = await db.get_vibes_page(code, page)
    if not rows:
        await cq.message.answer(t(lang, "vibes_empty"))
        return await cq.answer()

    lines = [t(lang, "vibes_header", page=page + 1), ""]
    for r in rows:
        lines.append(f"{_mode_label(r['mode'], lang)}\n«{r['text']}»\n")
    await cq.message.answer(
        "\n".join(lines),
        reply_markup=vibes_pagination(lang, page, has_next),
    )
    await cq.answer()


# --------------------------------------------------------------------------
# Owner: duel / feed / premium
# --------------------------------------------------------------------------
@dp.callback_query(F.data == "duel")
async def cb_duel(cq: CallbackQuery):
    user = await db.get_user(cq.from_user.id)
    if not user:
        return await cq.answer()
    lang = user["lang"]
    link = link_for(f"duel_{user['link_code']}")
    await cq.message.answer(t(lang, "duel", link=link))
    await cq.answer()


@dp.callback_query(F.data == "feed")
async def cb_feed(cq: CallbackQuery):
    user = await db.get_user(cq.from_user.id)
    lang = user["lang"] if user else lang_of(cq.from_user.language_code)
    pool = await db.recent_feed(limit=50)
    if not pool:
        await cq.message.answer(t(lang, "feed_empty"))
        return await cq.answer()
    sample = random.sample(pool, min(FEED_SAMPLE, len(pool)))
    lines = [t(lang, "feed_header"), ""]
    for r in sample:
        lines.append(t(lang, "feed_item", text=r["text"]))
    await cq.message.answer("\n\n".join(lines))
    await cq.answer()


@dp.callback_query(F.data == "premium")
async def cb_premium(cq: CallbackQuery):
    user = await db.get_user(cq.from_user.id)
    lang = user["lang"] if user else lang_of(cq.from_user.language_code)
    if user and user.get("is_premium"):
        await cq.message.answer(t(lang, "premium_already"))
    else:
        await cq.message.answer(t(lang, "premium_info", stars=299),
                                reply_markup=premium_kb(lang))
    await cq.answer()


@dp.callback_query(F.data == "buy_premium")
async def cb_buy_premium(cq: CallbackQuery):
    user = await db.get_user(cq.from_user.id)
    lang = user["lang"] if user else lang_of(cq.from_user.language_code)
    if user and user.get("is_premium"):
        return await cq.answer(t(lang, "premium_already"), show_alert=True)
    await send_premium_invoice(bot, cq.from_user.id, lang)
    await cq.answer()


# --------------------------------------------------------------------------
# Owner: story hint + report
# --------------------------------------------------------------------------
@dp.callback_query(F.data.startswith("story:"))
async def cb_story(cq: CallbackQuery):
    user = await db.get_user(cq.from_user.id)
    lang = user["lang"] if user else lang_of(cq.from_user.language_code)
    from config import BOT_USERNAME
    await cq.answer()
    await cq.message.answer(t(lang, "reply_story_hint", bot=BOT_USERNAME))


@dp.callback_query(F.data.startswith("report:"))
async def cb_report(cq: CallbackQuery):
    vibe_id = cq.data.split(":", 1)[1]
    user = await db.get_user(cq.from_user.id)
    lang = user["lang"] if user else lang_of(cq.from_user.language_code)

    vibe = await db.get_vibe(vibe_id)
    if vibe:
        await db.report_vibe(vibe_id)
        if vibe.get("from_hash"):
            await block_sender(vibe["from_hash"])
        if ADMIN_ID:
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"🚫 Report\nmode={vibe.get('mode')}\ntext={vibe.get('text')}",
                )
            except Exception:
                pass
    await cq.answer(t(lang, "reported_ok"), show_alert=True)
    try:
        await cq.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


# --------------------------------------------------------------------------
# Payments (Telegram Stars)
# --------------------------------------------------------------------------
@dp.pre_checkout_query()
async def pre_checkout(pcq: PreCheckoutQuery):
    await pcq.answer(ok=True)


@dp.message(F.successful_payment)
async def on_paid(message: Message):
    payment = message.successful_payment
    lang = lang_of(message.from_user.language_code)
    user = await db.get_user(message.from_user.id)
    if user:
        lang = user["lang"]
    if payment.invoice_payload == PREMIUM_PAYLOAD:
        await db.set_premium(message.from_user.id, True)
        await message.answer(t(lang, "pay_success"))
