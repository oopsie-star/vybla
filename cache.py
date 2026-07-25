"""Redis: rate limiting, 24h report blocks, and group real-activity tracking."""
import hashlib

from redis.asyncio import from_url

from config import (
    REDIS_URL, HASH_SALT, GUEST_RATELIMIT_SECONDS, REPORT_BLOCK_SECONDS,
    DIALOGUE_ACTIVITY_WINDOW_HOURS,
)

redis = from_url(REDIS_URL, decode_responses=True)
_ACTIVITY_WINDOW_SECONDS = DIALOGUE_ACTIVITY_WINDOW_HOURS * 3600


def sender_hash(from_id: int, to_code: str) -> str:
    """Stable, non-reversible sender fingerprint. Never store real ids in vibes."""
    raw = f"{from_id}:{to_code}:{HASH_SALT}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


async def allow_guest(from_id: int, to_code: str) -> bool:
    """True if allowed to send now; sets a 5-min lock (atomic SET NX EX)."""
    key = f"guest:{from_id}:{to_code}"
    ok = await redis.set(key, "1", nx=True, ex=GUEST_RATELIMIT_SECONDS)
    return bool(ok)


async def guest_locked(from_id: int, to_code: str) -> bool:
    """Peek the rate-limit lock without setting it."""
    return bool(await redis.exists(f"guest:{from_id}:{to_code}"))


async def is_blocked(from_hash: str) -> bool:
    return bool(await redis.exists(f"blocked:{from_hash}"))


async def block_sender(from_hash: str) -> None:
    await redis.set(f"blocked:{from_hash}", "1", ex=REPORT_BLOCK_SECONDS)


async def bump_real_activity(group_id: str) -> None:
    """Count one real (non-bot) group message in a rolling window. Used to
    auto-throttle the AI banter down once the group has organic activity."""
    key = f"real_activity:{group_id}"
    val = await redis.incr(key)
    if val == 1:
        await redis.expire(key, _ACTIVITY_WINDOW_SECONDS)


async def get_real_activity(group_id: str) -> int:
    val = await redis.get(f"real_activity:{group_id}")
    return int(val) if val else 0
