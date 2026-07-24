"""Telegram Stars (XTR) payments. Honest premium only — no fake 'reveal'."""
from aiogram import Bot
from aiogram.types import LabeledPrice

from config import t, PREMIUM_PRICE_STARS

PREMIUM_PAYLOAD = "vybla_premium"


async def send_premium_invoice(bot: Bot, chat_id: int, lang: str) -> None:
    await bot.send_invoice(
        chat_id=chat_id,
        title=t(lang, "pay_title"),
        description=t(lang, "pay_desc"),
        payload=PREMIUM_PAYLOAD,
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label="VYBLA+", amount=PREMIUM_PRICE_STARS)],
    )
