"""In-process background scheduler. Started from webhook.py lifespan.

Runs as long as the web service is awake. On Render's free tier the service
sleeps after ~15 min idle, so keep a pinger (e.g. cron-job.org) hitting `/`
every 10 min — that both wakes it and keeps these loops alive.
"""
import asyncio
import logging

from aiogram import Bot

from channel import autopost_vibe, post_top
from config import AUTOPOST_MINUTES, TOP_MINUTES

log = logging.getLogger("vybla.scheduler")

_tasks: list[asyncio.Task] = []


async def _every(seconds: int, coro, bot: Bot, initial_delay: int) -> None:
    await asyncio.sleep(initial_delay)
    while True:
        try:
            await coro(bot)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("scheduled task %s failed: %s", getattr(coro, "__name__", coro), e)
        await asyncio.sleep(seconds)


def start(bot: Bot) -> None:
    _tasks.append(asyncio.create_task(
        _every(AUTOPOST_MINUTES * 60, autopost_vibe, bot, initial_delay=60)))
    _tasks.append(asyncio.create_task(
        _every(TOP_MINUTES * 60, post_top, bot, initial_delay=120)))
    log.info("scheduler started: autopost=%dm top=%dm", AUTOPOST_MINUTES, TOP_MINUTES)


async def stop() -> None:
    for task in _tasks:
        task.cancel()
    for task in _tasks:
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    _tasks.clear()
