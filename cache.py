"""Redis: rate limiting and 24h report blocks."""
import hashlib

from redis.asyncio import from_url

from config import REDIS_URL, HASH_SALT, GUEST_RATELIMIT_SECONDS, REPORT_BLOCK_SECONDS

redis = from_url(REDIS_URL, decode_responses=True)


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
