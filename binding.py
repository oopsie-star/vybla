"""Runtime cache of the channel/group the bot is bound to.

The bot captures these automatically the moment it is promoted to admin in a
channel/group (see the my_chat_member handler in bot.py), and persists them in
the `system` table so they survive restarts. No manual id config needed.
"""
import logging

import db

log = logging.getLogger("vybla.binding")

_state: dict[str, str | None] = {"channel_id": None, "group_id": None}


async def load() -> None:
    """Best-effort load from the system table on startup."""
    try:
        _state["channel_id"] = await db.get_system("channel_id")
        _state["group_id"] = await db.get_system("group_id")
        log.info("binding loaded: %s", _state)
    except Exception as e:
        # system table may not exist yet on a fresh DB — stay unbound.
        log.warning("binding load skipped: %s", e)


def channel_id() -> str | None:
    return _state["channel_id"]


def group_id() -> str | None:
    return _state["group_id"]


async def set_channel(cid: int) -> None:
    _state["channel_id"] = str(cid)
    await db.set_system("channel_id", str(cid))


async def set_group(gid: int) -> None:
    _state["group_id"] = str(gid)
    await db.set_system("group_id", str(gid))
