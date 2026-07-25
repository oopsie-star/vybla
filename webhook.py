"""FastAPI webhook entrypoint.

Run:  uvicorn webhook:app --host 0.0.0.0 --port 8000
On startup it registers the webhook at {WEBHOOK_URL}/webhook/{BOT_TOKEN}.
"""
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, FileResponse
from starlette.background import BackgroundTask
from aiogram.types import Update

from bot import bot, dp
import binding
import scheduler
import db
import cards
import avatars
from config import (
    WEBHOOK_PATH, WEBHOOK_FULL, WEBHOOK_SECRET, WEBHOOK_URL, BOT_USERNAME, t,
)

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
        # NOTE: do NOT delete_webhook() here. On Render's zero-downtime deploys
        # the old instance shuts down AFTER the new one has already re-set the
        # webhook, so deleting here would wipe the live webhook. The webhook is
        # (re)set on every startup instead.
        await scheduler.stop()
        await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.api_route("/", methods=["GET", "HEAD"])
async def health():
    # Render's port scan / health check may use HEAD — answer both, never 405.
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


# --------------------------------------------------------------------------
# Share-to-story mini app. Opened from the "Ответить в сторис" web_app button
# (see keyboards.vibe_actions). It calls Telegram's native
# WebApp.shareToStory(), which opens the story editor pre-filled with the
# card image and a tappable link back to the bot — one tap, no manual
# save-and-post. Only available on recent mobile Telegram clients; older/
# desktop clients fall back to the in-page instructions below.
# --------------------------------------------------------------------------
_STORY_HTML = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
body{{margin:0;background:#000;color:#fff;font-family:-apple-system,Segoe UI,sans-serif;
display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;
padding:24px;box-sizing:border-box}}
#msg{{max-width:420px;line-height:1.5}}
</style></head>
<body>
<div id="msg">...</div>
<script>
var tg = window.Telegram && window.Telegram.WebApp;
if (tg) {{ tg.ready(); }}
var mediaUrl = {media_url};
var caption = {caption};
var botLink = {bot_link};
var widgetName = {widget_name};
var fallbackHtml = {fallback_html};
function showFallback() {{ document.getElementById('msg').innerHTML = fallbackHtml; }}
if (tg && tg.shareToStory) {{
  try {{
    tg.shareToStory(mediaUrl, {{ text: caption, widget_link: {{ url: botLink, name: widgetName }} }});
    setTimeout(function () {{ tg.close(); }}, 400);
  }} catch (e) {{ showFallback(); }}
}} else {{
  showFallback();
}}
</script>
</body></html>"""


@app.get("/story/{vibe_id}", response_class=HTMLResponse)
async def story_page(vibe_id: str, lang: str = "ru", code: str = ""):
    lang = "en" if lang == "en" else "ru"
    bot_link = f"https://t.me/{BOT_USERNAME}?start=ref_{code}" if code else f"https://t.me/{BOT_USERNAME}"
    media_url = f"{WEBHOOK_URL}/card/{vibe_id}.png"
    # The link is baked into the caption text too (not just the widget_link
    # sticker), so it stays visible even if Telegram restricts widget_link
    # for this bot category.
    caption = f"{t(lang, 'story_caption')} {bot_link}"
    html = _STORY_HTML.format(
        media_url=json.dumps(media_url),
        caption=json.dumps(caption),
        bot_link=json.dumps(bot_link),
        widget_name=json.dumps(t(lang, "story_widget_name")),
        fallback_html=json.dumps(t(lang, "story_fallback", link=bot_link)),
    )
    return HTMLResponse(html)


@app.get("/card/{vibe_id}.png")
async def card_image(vibe_id: str):
    vibe = await db.get_vibe(vibe_id)
    if not vibe:
        return Response(status_code=404)
    owner = await db.get_user_by_code(vibe["to_user_code"])
    avatar = await avatars.download_avatar(bot, owner["id"]) if owner else None
    watermark = not (owner and owner.get("is_premium"))
    path = cards.generate_vibe_card(
        vibe["text"], vibe["mode"], avatar_path=avatar, watermark=watermark,
    )

    def _cleanup(paths=(path, avatar)):
        for p in paths:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    return FileResponse(path, media_type="image/png", background=BackgroundTask(_cleanup))
