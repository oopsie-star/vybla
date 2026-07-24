"""Supabase data access. supabase-py is sync, so every call is pushed to a
thread with asyncio.to_thread to keep the bot fully async."""
import asyncio
import secrets
import string

from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY, VIBES_PAGE_SIZE

_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
_ALPHABET = string.ascii_uppercase + string.digits  # A-Z0-9


async def _x(builder):
    """Execute a supabase query builder off the event loop."""
    return await asyncio.to_thread(builder.execute)


# --- users -----------------------------------------------------------------
async def get_user(user_id: int) -> dict | None:
    res = await _x(_client.table("users").select("*").eq("id", user_id).limit(1))
    return res.data[0] if res.data else None


async def get_user_by_code(code: str) -> dict | None:
    res = await _x(_client.table("users").select("*").eq("link_code", code).limit(1))
    return res.data[0] if res.data else None


async def _code_exists(code: str) -> bool:
    res = await _x(_client.table("users").select("id").eq("link_code", code).limit(1))
    return bool(res.data)


async def _gen_unique_code() -> str:
    for _ in range(10):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(6))
        if not await _code_exists(code):
            return code
    raise RuntimeError("Could not generate a unique link_code")


async def get_or_create_user(
    user_id: int, username: str | None, lang: str, referred_by: str | None = None,
) -> tuple[dict, bool]:
    """Return (user_row, was_just_created). referred_by is only ever applied on
    creation — an existing user's referrer can't be changed after the fact."""
    existing = await get_user(user_id)
    if existing:
        if username and username != existing.get("username"):
            await _x(_client.table("users").update({"username": username}).eq("id", user_id))
            existing["username"] = username
        return existing, False
    code = await _gen_unique_code()
    row = {"id": user_id, "username": username, "link_code": code, "lang": lang}
    if referred_by and referred_by != code:
        row["referred_by"] = referred_by
    res = await _x(_client.table("users").insert(row))
    return res.data[0], True


async def set_premium(user_id: int, value: bool = True) -> None:
    await _x(_client.table("users").update({"is_premium": value}).eq("id", user_id))


async def increment_views(code: str) -> None:
    await asyncio.to_thread(_client.rpc("increment_user_views", {"p_code": code}).execute)


async def increment_vibes(code: str) -> None:
    await asyncio.to_thread(_client.rpc("increment_user_vibes", {"p_code": code}).execute)


async def register_referral(referrer_code: str) -> tuple[int | None, bool]:
    """Bump referrer_code's referral_count; auto-grants VYBLA+ at the goal.
    Returns (new_count, reward_just_granted). new_count is None if the
    referrer code doesn't exist."""
    res = await asyncio.to_thread(
        _client.rpc("register_referral", {"p_referrer_code": referrer_code}).execute
    )
    if not res.data:
        return None, False
    row = res.data[0]
    return row.get("new_count"), bool(row.get("reward_granted"))


# --- vibes -----------------------------------------------------------------
async def add_vibe(to_code: str, from_hash: str, mode: str, text: str) -> dict:
    row = {"to_user_code": to_code, "from_hash": from_hash, "mode": mode, "text": text}
    res = await _x(_client.table("vibes").insert(row))
    return res.data[0]


async def count_unread(code: str) -> int:
    res = await _x(
        _client.table("vibes").select("id", count="exact")
        .eq("to_user_code", code).eq("is_read", False)
    )
    return res.count or 0


async def get_vibes_page(code: str, page: int) -> tuple[list[dict], bool]:
    """Return (rows, has_next) for a 0-indexed page."""
    start = page * VIBES_PAGE_SIZE
    end = start + VIBES_PAGE_SIZE  # fetch one extra to detect next page
    res = await _x(
        _client.table("vibes").select("*")
        .eq("to_user_code", code)
        .order("created_at", desc=True)
        .range(start, end)
    )
    rows = res.data or []
    has_next = len(rows) > VIBES_PAGE_SIZE
    return rows[:VIBES_PAGE_SIZE], has_next


async def mark_read(code: str) -> None:
    await _x(
        _client.table("vibes").update({"is_read": True})
        .eq("to_user_code", code).eq("is_read", False)
    )


async def report_vibe(vibe_id: str) -> dict | None:
    res = await _x(
        _client.table("vibes").update({"is_reported": True}).eq("id", vibe_id)
    )
    return res.data[0] if res.data else None


async def get_vibe(vibe_id: str) -> dict | None:
    res = await _x(_client.table("vibes").select("*").eq("id", vibe_id).limit(1))
    return res.data[0] if res.data else None


async def recent_feed(limit: int = 50) -> list[dict]:
    res = await _x(
        _client.table("vibes").select("text,mode,created_at")
        .eq("is_reported", False)
        .order("created_at", desc=True)
        .limit(limit)
    )
    return res.data or []


async def count_all_vibes() -> int:
    res = await _x(
        _client.table("vibes").select("id", count="exact").eq("is_reported", False)
    )
    return res.count or 0


# --- system key/value + leaderboard (autonomous layer) ---------------------
async def get_system(key: str) -> str | None:
    res = await _x(_client.table("system").select("value").eq("key", key).limit(1))
    return res.data[0]["value"] if res.data else None


async def set_system(key: str, value: str) -> None:
    await _x(_client.table("system").upsert({"key": key, "value": value}))


async def get_top_users(limit: int = 3) -> list[dict]:
    res = await _x(
        _client.table("users").select("link_code,total_views,total_vibes")
        .order("total_views", desc=True).limit(limit)
    )
    return res.data or []
