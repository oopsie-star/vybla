"""Content moderation for incoming vibes."""
import re

# Block links / handles: keeps the bot off Telegram's spam radar and stops
# anonymous messages from being used to phish or redirect people.
_LINK_RE = re.compile(r"(https?://|www\.|t\.me/|telegram\.me/|@[a-z0-9_]{3,})", re.IGNORECASE)

# Minimal safety wordlist. Extend as needed; kept short on purpose so it's
# reviewable. Matches whole words, case-insensitive, ru + en.
_BANNED = [
    "suicide", "kill yourself", "kys", "drugs", "cocaine", "heroin",
    "суицид", "убей себя", "сдохни", "наркотик", "наркота",
]
_BANNED_RE = re.compile(
    r"(?<![\w])(" + "|".join(re.escape(w) for w in _BANNED) + r")(?![\w])",
    re.IGNORECASE,
)


def moderate(text: str) -> tuple[bool, str | None]:
    """Return (ok, reason_key). reason_key is None when ok."""
    stripped = text.strip()
    if not stripped:
        return False, "mod_blocked"
    if "@" in stripped or _LINK_RE.search(stripped):
        return False, "mod_blocked"
    if _BANNED_RE.search(stripped):
        return False, "mod_blocked"
    return True, None
