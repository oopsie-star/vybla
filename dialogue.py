"""AI banter for the group: a short scripted-style dialogue between two named
characters (Ева / Макс), posted by the single VYBLA bot as one formatted
message — not simulated separate Telegram accounts. This is a transparent
content format (like a mini comic strip), not an impersonation of real users:
Telegram already tags the poster as "bot", and the "Ева и Макс обсуждают"
framing makes clear it's an authored bit, not a live human conversation.

Generated live via OpenRouter when OPENROUTER_API_KEY is set; falls back to a
curated scripted bank on missing key, API error, or unparsable output — the
feature never breaks the group even if the key is wrong or exhausted.

Auto-throttle: once the group has real (non-bot) activity of its own (see
cache.bump_real_activity, wired from bot.py's moderate_group), posting here
backs off — see post_dialogue().
"""
import logging
import random

import httpx
from aiogram import Bot

import binding
import cache
from config import (
    BOT_USERNAME, OPENROUTER_API_KEY, OPENROUTER_MODEL,
    DIALOGUE_ACTIVITY_THRESHOLD,
)

log = logging.getLogger("vybla.dialogue")

PERSONAS = "Ева (наблюдательная, с лёгким сарказмом, топит за честность) и Макс (эмоциональный, делится личным, немного наивный)"

TOPICS = [
    "ред флаги в отношениях",
    "грин флаги, которые недооценивают",
    "получить анонимный комплимент от незнакомца",
    "признаться в чувствах анонимно",
    "смешная анонимка, которая оказалась правдой",
    "почему людям проще быть честными анонимно",
    "как понять, что тебе врут",
    "доверие в отношениях",
    "стоит ли писать бывшему(ей) анонимный вайб",
    "самый неожиданный комплимент, который можно получить",
]

_SYSTEM_PROMPT = (
    "Ты пишешь короткий, живой диалог между двумя вымышленными персонажами "
    f"Telegram-группы VYBLA (анонимные честные сообщения — комплименты, ред-флаги, "
    f"признания). Персонажи: {PERSONAS}.\n\n"
    "Правила:\n"
    "- 4-6 реплик, чередуя персонажей, разговорный русский\n"
    "- каждая реплика короткая, до 15 слов\n"
    "- можно 1-2 эмодзи на весь диалог, не больше\n"
    "- без ссылок, без реальных имён и данных людей, без мата и оскорблений\n"
    "- дружелюбно-подкалывающий тон, тема строго про отношения/честность/анонимность\n"
    "- это художественный диалог для развлечения, не утверждай, что это реальная переписка\n\n"
    "Формат вывода СТРОГО построчно, без пояснений и без markdown:\n"
    "Ева: ...\n"
    "Макс: ...\n"
    "(и так далее, максимум 6 строк)"
)

# Used when OPENROUTER_API_KEY is unset, the call fails, or the model output
# doesn't parse — the feature must never break the group.
_FALLBACK_DIALOGUES = [
    [("Ева", "чувак прислал мне «ты как дорогой парфюм» анонимно"),
     ("Макс", "это грин флаг или он просто начитался тик-тока?"),
     ("Ева", "не знаю, но приятно 🙂"),
     ("Макс", "мне вчера ред флаг пришёл: «ты слишком много думаешь»"),
     ("Ева", "это НЕ ред флаг, это же правда"),
     ("Макс", "вот именно поэтому я и обиделся")],
    [("Макс", "как думаешь, люди честнее анонимно или в лицо?"),
     ("Ева", "анонимно, стопроцентно"),
     ("Макс", "а если это просто повод быть грубым?"),
     ("Ева", "тогда это не честность, а трусость с эмодзи")],
    [("Ева", "мне кажется, ред флаги реально недооценивают"),
     ("Макс", "например?"),
     ("Ева", "когда человек никогда не признаёт свою неправоту"),
     ("Макс", "…я записываю"),
     ("Ева", "себе, надеюсь")],
    [("Макс", "получил анонимку «у тебя вайб дорогой бывшей»"),
     ("Ева", "это комплимент или диагноз?"),
     ("Макс", "я решил, что комплимент"),
     ("Ева", "здоровый подход, уважаю")],
    [("Ева", "грин флаг — это когда человек говорит «мне надо подумать»"),
     ("Макс", "а не сразу «да» или скандал?"),
     ("Ева", "именно"),
     ("Макс", "тогда я 70% грин флаг")],
    [("Макс", "стоит писать бывшей анонимный вайб?"),
     ("Ева", "смотря что хочешь сказать"),
     ("Макс", "что-то доброе, честно"),
     ("Ева", "тогда пиши. если хочешь уколоть — не надо")],
    [("Ева", "самое честное, что мне анонимно написали — «ты классный, но опаздываешь всегда»"),
     ("Макс", "жёстко"),
     ("Ева", "зато правда"),
     ("Макс", "правда обычно и жёсткая")],
    [("Макс", "думаю, доверие строится на мелочах"),
     ("Ева", "например на том, что ты вернул книгу вовремя"),
     ("Макс", "уже 3 года несу эту книгу как крест"),
     ("Ева", "вот и ред флаг нашли")],
]


async def _generate_via_openrouter(topic: str) -> list[tuple[str, str]] | None:
    if not OPENROUTER_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": f"Тема: {topic}"},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.9,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        raw = data["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning("openrouter call failed, falling back: %s", e)
        return None

    lines: list[tuple[str, str]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        speaker, _, rest = line.partition(":")
        speaker = speaker.strip().lstrip("-•* ").strip()
        rest = rest.strip()
        if speaker.lower() in ("ева", "макс") and rest:
            lines.append((speaker.capitalize(), rest))
    return lines if len(lines) >= 2 else None


def _fallback_dialogue() -> list[tuple[str, str]]:
    return random.choice(_FALLBACK_DIALOGUES)


async def generate_dialogue() -> list[tuple[str, str]]:
    topic = random.choice(TOPICS)
    lines = await _generate_via_openrouter(topic)
    return lines if lines else _fallback_dialogue()


async def post_dialogue(bot: Bot) -> None:
    gid = binding.group_id()
    if not gid:
        return

    activity = await cache.get_real_activity(gid)
    if activity >= DIALOGUE_ACTIVITY_THRESHOLD:
        log.info("group has real activity (%d) — skipping AI banter", activity)
        return

    lines = await generate_dialogue()
    body = "\n".join(f"{speaker}: {text}" for speaker, text in lines)
    message = f"🎭 Ева и Макс обсуждают:\n\n{body}\n\nа у тебя как? → @{BOT_USERNAME}"
    try:
        await bot.send_message(int(gid), message)
    except Exception as e:
        log.warning("dialogue post failed: %s", e)
