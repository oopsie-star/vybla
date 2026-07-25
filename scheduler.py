"""In-process background scheduler. Started from webhook.py lifespan.

Runs as long as the web service is awake. On Render's free tier the service
sleeps after ~15 min idle, so keep a pinger (e.g. cron-job.org) hitting `/`
every 10 min — that both wakes it and keeps these loops alive.
"""
import asyncio
import logging

from aiogram import Bot

from channel import autopost_vibe, post_top, post_group_spotlight
from editorial import post_editorial, post_poll
from dialogue import post_dialogue
from config import (
    AUTOPOST_MINUTES, TOP_MINUTES, SPOTLIGHT_MINUTES,
    EDITORIAL_MINUTES, POLL_MINUTES, DIALOGUE_MINUTES,
)

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
    # Staggered initial delays so none of these fire in the same instant.
    _tasks.append(asyncio.create_task(
        _every(AUTOPOST_MINUTES * 60, autopost_vibe, bot, initial_delay=60)))
    _tasks.append(asyncio.create_task(
        _every(TOP_MINUTES * 60, post_top, bot, initial_delay=180)))
    _tasks.append(asyncio.create_task(
        _every(SPOTLIGHT_MINUTES * 60, post_group_spotlight, bot, initial_delay=300)))
    _tasks.append(asyncio.create_task(
        _every(EDITORIAL_MINUTES * 60, post_editorial, bot, initial_delay=420)))
    _tasks.append(asyncio.create_task(
        _every(POLL_MINUTES * 60, post_poll, bot, initial_delay=540)))
    _tasks.append(asyncio.create_task(
        _every(DIALOGUE_MINUTES * 60, post_dialogue, bot, initial_delay=660)))
    log.info(
        "scheduler started: autopost=%dm top=%dm spotlight=%dm editorial=%dm poll=%dm dialogue=%dm",
        AUTOPOST_MINUTES, TOP_MINUTES, SPOTLIGHT_MINUTES, EDITORIAL_MINUTES, POLL_MINUTES,
        DIALOGUE_MINUTES,
    )


async def stop() -> None:
    for task in _tasks:
        task.cancel()
    for task in _tasks:
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    _tasks.clear()
