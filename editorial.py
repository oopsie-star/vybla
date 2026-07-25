"""Standalone value content — not sourced from real vibes. This is what gives
the channel/group something worth following even for people who don't use
the bot yet: real psychology/relationship content on-topic for the audience
an anonymous-feedback app naturally attracts, plus native Telegram polls in
the group for actual interaction (not just browsing).

Everything here is either genuine informational content or a real Telegram
poll — never a fabricated "anonymous message" pretending to be a real
submission. That would break the same honesty principle behind the no-fake-
hints and no-fake-metrics decisions elsewhere in this project.
"""
import logging
import random

from aiogram import Bot

import binding
from config import BOT_USERNAME

log = logging.getLogger("vybla.editorial")

# Short, on-topic content for the audience an anonymous-feedback app
# attracts: relationship psychology, red/green flags, honesty. Each ends
# with a soft one-liner, not a hard sell every time.
FACTS = [
    "🚩 Ред флаг, который часто не замечают: партнёр, который никогда не признаёт свою неправоту. Это не характер — это паттерн.",
    "Психологи отмечают: анонимная обратная связь в среднем честнее, чем сказанная в лицо — меньше страха реакции, меньше социальной желательности.",
    "🟢 Грин флаг: человек, который может сказать «мне нужно подумать» вместо того, чтобы сразу взрываться или сразу соглашаться.",
    "Забавный факт: люди точнее оценивают себя, когда получают обратную связь анонимно, а не публично.",
    "🚩 Если тебе регулярно приходится доказывать, что ты не «слишком остро реагируешь» — это ред флаг у собеседника, а не твоя гиперчувствительность.",
    "Честность растёт вместе с анонимностью — это не баг человеческой психики, а хорошо изученный эффект в соц. психологии.",
    "🟢 Грин флаг: спрашивает «как тебе удобнее» вместо того, чтобы решать за тебя.",
    "Комплимент, сказанный анонимно, воспринимается как более искренний — именно потому, что отправителю нечего было выигрывать.",
    "🚩 Постоянное «ты слишком чувствительный(ая)» в ответ на границы — классика газлайтинга, а не безобидная фраза.",
    "Интересно: людям проще признаться в симпатии анонимно, чем лично — страх отказа работает как реальный физический стресс.",
    "🟢 Грин флаг: не читает переписки за спиной, а прямо спрашивает то, что хочет узнать.",
    "Ред флаги редко бывают одиночными — если заметил один, оглянись, обычно рядом ещё 2-3.",
    "🚩 Обесценивание твоих достижений («ну это несложно было») — тихий, но частый ред флаг.",
    "Анонимные комплименты запоминаются дольше публичных — меньше подозрения в лести, больше доверия к искренности.",
    "🟢 Грин флаг: извиняется конкретно, а не размытым «ну извини, если что».",
]

# Native Telegram polls posted to the group — an actual interactive format,
# not just something to scroll past.
POLLS = [
    ("Что бы ты хотел(а) узнать о себе анонимно?",
     ["Как меня видят на самом деле", "Мои ред флаги", "Кто по мне сохнет 👀", "Мне и так норм"]),
    ("Люди в среднем честнее...",
     ["Анонимно", "В лицо", "Одинаково"]),
    ("Самый частый повод для ред флага в отношениях?",
     ["Ревность", "Игнор", "Ложь", "Не слушает"]),
    ("Ты бы предпочёл(а) получить анонимно...",
     ["🔥 Комплимент", "🚩 Ред флаг", "💔 Признание в чувствах"]),
    ("Тебе когда-нибудь писали анонимно то, что оказалось правдой?",
     ["Да, и это было жёстко", "Да, было приятно", "Ещё нет"]),
    ("Что сложнее сказать человеку в лицо?",
     ["Комплимент", "Критику", "Что нравится"]),
]

_last_fact_idx: int | None = None
_last_poll_idx: int | None = None


def _pick(pool: list, last_idx: int | None) -> tuple:
    idx = random.randrange(len(pool))
    if len(pool) > 1:
        while idx == last_idx:
            idx = random.randrange(len(pool))
    return idx, pool[idx]


async def post_editorial(bot: Bot) -> None:
    global _last_fact_idx
    cid = binding.channel_id()
    if not cid:
        return
    idx, fact = _pick(FACTS, _last_fact_idx)
    _last_fact_idx = idx
    text = f"{fact}\n\nсвоя ссылка → @{BOT_USERNAME}"
    try:
        await bot.send_message(int(cid), text)
    except Exception as e:
        log.warning("editorial post failed: %s", e)


async def post_poll(bot: Bot) -> None:
    global _last_poll_idx
    gid = binding.group_id()
    if not gid:
        return
    idx, (question, options) = _pick(POLLS, _last_poll_idx)
    _last_poll_idx = idx
    try:
        await bot.send_poll(int(gid), question=question, options=options, is_anonymous=True)
    except Exception as e:
        log.warning("poll post failed: %s", e)
