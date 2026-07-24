"""FastAPI webhook entrypoint.

Run:  uvicorn webhook:app --host 0.0.0.0 --port 8000
On startup it registers the webhook at {WEBHOOK_URL}/webhook/{BOT_TOKEN}.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from aiogram.types import Update

from bot import bot, dp
import binding
import scheduler
from config import WEBHOOK_PATH, WEBHOOK_FULL, WEBHOOK_SECRET

log = logging.getLogger("vybla.webhook")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await bot.set_webhook(
        url=WEBHOOK_FULL,
        allowed_updates=dp.resolve_used_update_types(),
        secret_token=WEBHOOK_SECRET or None,
        drop_pending_updates=True,
    )
    log.info("Webhook set to %s", WEBHOOK_FULL)
    await binding.load()          # restore bound channel/group ids
    scheduler.start(bot)          # autopost + hourly leaderboard loops
    try:
        yield
    finally:
        await scheduler.stop()
        await bot.delete_webhook()
        await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def health():
    return {"status": "ok", "service": "vybla"}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    # Verify Telegram's secret header if configured.
    if WEBHOOK_SECRET:
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
            return Response(status_code=403)
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return Response(status_code=200)
