"""Central config: env vars, constants, i18n texts."""
import os
from dotenv import load_dotenv

load_dotenv()


def _req(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


# --- Secrets / connections -------------------------------------------------
BOT_TOKEN = _req("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "vybla_bot").lstrip("@")

# Accept a URL even if pasted with a trailing "/rest/v1/" — supabase-py wants
# just the project base URL and appends the REST path itself.
SUPABASE_URL = _req("SUPABASE_URL").rstrip("/")
for _suffix in ("/rest/v1", "/rest"):
    if SUPABASE_URL.endswith(_suffix):
        SUPABASE_URL = SUPABASE_URL[: -len(_suffix)]
SUPABASE_KEY = _req("SUPABASE_KEY")

# Tolerate an accidental duplicated "REDIS_URL=" prefix in the value.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
if REDIS_URL.startswith("REDIS_URL="):
    REDIS_URL = REDIS_URL[len("REDIS_URL="):]
WEBHOOK_URL = _req("WEBHOOK_URL").rstrip("/")
HASH_SALT = os.getenv("HASH_SALT", "change_me")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")  # gets report alerts

# --- Webhook ---------------------------------------------------------------
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_FULL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# --- Tunables --------------------------------------------------------------
GUEST_RATELIMIT_SECONDS = 5 * 60      # 1 message per link per 5 min
REPORT_BLOCK_SECONDS = 24 * 60 * 60   # reported sender blocked 24h
MAX_VIBE_LEN = 120
FEED_SAMPLE = 5
VIBES_PAGE_SIZE = 5
PREMIUM_PRICE_STARS = 299
REFERRAL_GOAL = 3  # invite this many -> free VYBLA+. Must match supabase.sql register_referral().

# --- Autonomous layer ------------------------------------------------------
# The bot auto-captures the channel/group ids when it is promoted to admin
# (see the my_chat_member handler), so no manual id config is needed.
AUTOPOST_MINUTES = int(os.getenv("AUTOPOST_MINUTES", "30"))  # channel card-post cadence
TOP_MINUTES = int(os.getenv("TOP_MINUTES", "60"))            # group leaderboard cadence
SPOTLIGHT_MINUTES = int(os.getenv("SPOTLIGHT_MINUTES", "120"))  # group discussion-card cadence
EDITORIAL_MINUTES = int(os.getenv("EDITORIAL_MINUTES", "90"))   # channel fact/tip cadence
POLL_MINUTES = int(os.getenv("POLL_MINUTES", "180"))             # group native-poll cadence

# AI "banter" between two on-brand characters (Ева/Макс), posted to the group
# as a single formatted dialogue by the bot — not simulated separate accounts.
# Auto-throttles down once the group has real activity of its own.
DIALOGUE_MINUTES = int(os.getenv("DIALOGUE_MINUTES", "45"))
DIALOGUE_ACTIVITY_THRESHOLD = int(os.getenv("DIALOGUE_ACTIVITY_THRESHOLD", "8"))
DIALOGUE_ACTIVITY_WINDOW_HOURS = int(os.getenv("DIALOGUE_ACTIVITY_WINDOW_HOURS", "3"))
# OpenRouter (OpenAI-compatible). Leave OPENROUTER_API_KEY empty to use the
# free scripted fallback bank only — nothing breaks without a key.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# deepseek/deepseek-chat tested noticeably better for natural Russian than
# llama-3.1-8b-instruct (which mixed in English) and qwen-2.5-7b-instruct
# (which broke into Chinese mid-reply), at ~$0.0001/call — negligible cost.
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
# When True, non-link messages in the funnel group are removed. Set GROUP_STRICT=0
# to only remove foreign links/@handles and allow normal chat.
GROUP_STRICT = os.getenv("GROUP_STRICT", "1") == "1"

# mode -> emoji + labels. Gradients live in cards.py.
MODES = {
    "compliment": {"emoji": "🔥", "ru": "Комплимент", "en": "Compliment"},
    "redflag":    {"emoji": "🚩", "ru": "Ред флаг",   "en": "Red flag"},
    "crush":      {"emoji": "💔", "ru": "Краш",        "en": "Crush"},
    "custom":     {"emoji": "✍️", "ru": "Свое",         "en": "Custom"},
}


def link_for(code: str) -> str:
    return f"t.me/{BOT_USERNAME}?start={code}"


# --- i18n ------------------------------------------------------------------
TEXTS = {
    "ru": {
        "menu": (
            "VYBLA — твое зеркало.\n\n"
            "Твоя ссылка: {link}\n"
            "Просмотров: {views} | Вайбов: {vibes}\n\n"
            "Кидай в био. Через 5 минут офигеешь что пишут."
        ),
        "btn_my_vibes": "📩 Мои вайбы ({n})",
        "btn_copy": "🔗 Скопировать ссылку",
        "btn_duel": "⚔️ Вайб-Дуэль",
        "btn_feed": "🌍 Лента",
        "btn_premium": "⭐️ Premium",
        "btn_invite": "🎁 Пригласить друзей",

        "invite_info": (
            "🎁 Приглашай — получай Premium бесплатно\n\n"
            "Твоя пригласительная ссылка:\n{link}\n\n"
            "Приглашено: {count}/{goal}\n\n"
            "Как только по твоей ссылке зайдут {goal} новых человека — "
            "VYBLA+ включится сама, бесплатно 🖤"
        ),
        "invite_reward_dm": (
            "🎉 {goal} человек зашли по твоей ссылке!\n"
            "VYBLA+ активирован бесплатно — спасибо, что разносишь вайб 🖤"
        ),

        "broken_link": "Ссылка битая 🤷",
        "rate_limited": "Подожди 5 минут, не спамь 🙃",
        "blocked_sender": "Ты пока не можешь писать сюда.",
        "ask_mode": "Ты пишешь анонимно для @{owner}. Как ты его видишь?",
        "ask_text": "Напиши свой вайб (до {n} символов):",
        "too_long": "Слишком длинно. Максимум {n} символов.",
        "mod_blocked": "Попробуй мягче, без ссылок и лишнего 🙏",
        "sent_ok": "Отправлено анонимно! 🖤\nХочешь такую же ссылку для себя? Жми /start",
        "btn_create_own": "Создать свою ссылку",

        "new_vibe_caption": "Новый вайб 💬: {text}",
        "btn_reply_story": "↩️ Ответить в сторис",
        "btn_report": "🚫 Жалоба",
        "reported_ok": "Спасибо, вайб скрыт, отправитель заблокирован на 24ч.",
        "story_caption": "Мне анонимно написали в VYBLA 🖤",
        "story_widget_name": "VYBLA",
        "story_fallback": (
            "Не получилось открыть редактор историй автоматически "
            "(нужен свежий мобильный Telegram). Сохрани картинку выше и "
            "выложи в историю вручную, отметив: {link}"
        ),

        "vibes_empty": "Пока пусто. Кинь ссылку в био и жди 👀",
        "vibes_header": "Твои вайбы (стр. {page}):",
        "btn_prev": "‹ Назад",
        "btn_next": "Дальше ›",

        "duel": (
            "⚔️ Вайб-Дуэль\n\n"
            "У кого больше вайбов за 24ч? Кинь друзьям — принявший играет против тебя:\n"
            "{link}"
        ),
        "feed_header": "🌍 Лента (анонимно):",
        "feed_empty": "Лента пока пустая. Стань первым 🔥",
        "feed_item": "Кто-то написал: «{text}»",

        "premium_info": (
            "⭐️ VYBLA+ за {stars} Stars\n\n"
            "• все дизайны карточек\n"
            "• без вотермарки\n"
            "• статистика: режим, время, реакции\n"
            "• приоритет в ленте\n\n"
            "Честно: отправители остаются анонимными. Мы не продаем «угадайку», "
            "кто написал — это обман и путь к бану. Только реальные фишки."
        ),
        "premium_already": "У тебя уже VYBLA+ ⭐️ Спасибо!",
        "btn_buy_premium": "Купить за {stars} Stars",
        "reveal_honest": (
            "VYBLA держит отправителей анонимными by design 🖤\n"
            "Мы физически не показываем, кто написал, и не выдумываем подсказки. "
            "Зато VYBLA+ дает все дизайны и статистику — жми ⭐️ Premium."
        ),
        "pay_title": "VYBLA+",
        "pay_desc": "Все дизайны, без вотермарки, статистика.",
        "pay_success": "Готово! VYBLA+ активирован ⭐️🖤",

        "self_note": "(это твоя же ссылка, но ок — пиши себе)",
    },
    "en": {
        "menu": (
            "VYBLA — your mirror.\n\n"
            "Your link: {link}\n"
            "Views: {views} | Vibes: {vibes}\n\n"
            "Drop it in your bio. In 5 minutes you'll be shook."
        ),
        "btn_my_vibes": "📩 My vibes ({n})",
        "btn_copy": "🔗 Copy link",
        "btn_duel": "⚔️ Vibe Duel",
        "btn_feed": "🌍 Feed",
        "btn_premium": "⭐️ Premium",
        "btn_invite": "🎁 Invite friends",

        "invite_info": (
            "🎁 Invite friends — get Premium free\n\n"
            "Your invite link:\n{link}\n\n"
            "Invited: {count}/{goal}\n\n"
            "Once {goal} new people join through your link, VYBLA+ "
            "unlocks automatically, for free 🖤"
        ),
        "invite_reward_dm": (
            "🎉 {goal} people joined through your link!\n"
            "VYBLA+ is now active for free — thanks for spreading the vibe 🖤"
        ),

        "broken_link": "Broken link 🤷",
        "rate_limited": "Wait 5 minutes, don't spam 🙃",
        "blocked_sender": "You can't send here right now.",
        "ask_mode": "You're writing anonymously to @{owner}. How do you see them?",
        "ask_text": "Write your vibe (up to {n} chars):",
        "too_long": "Too long. Max {n} characters.",
        "mod_blocked": "Try softer, no links or spam 🙏",
        "sent_ok": "Sent anonymously! 🖤\nWant a link like this? Hit /start",
        "btn_create_own": "Create my link",

        "new_vibe_caption": "New vibe 💬: {text}",
        "btn_reply_story": "↩️ Reply in story",
        "btn_report": "🚫 Report",
        "reported_ok": "Thanks, vibe hidden, sender blocked for 24h.",
        "story_caption": "Someone sent me an anonymous vibe on VYBLA 🖤",
        "story_widget_name": "VYBLA",
        "story_fallback": (
            "Couldn't open the story editor automatically (needs a recent "
            "mobile Telegram). Save the card above and post it to your "
            "story manually, tagging: {link}"
        ),

        "vibes_empty": "Empty for now. Drop your link in bio and wait 👀",
        "vibes_header": "Your vibes (page {page}):",
        "btn_prev": "‹ Prev",
        "btn_next": "Next ›",

        "duel": (
            "⚔️ Vibe Duel\n\n"
            "Who gets more vibes in 24h? Send to friends — whoever accepts plays you:\n"
            "{link}"
        ),
        "feed_header": "🌍 Feed (anonymous):",
        "feed_empty": "Feed is empty. Be the first 🔥",
        "feed_item": "Someone wrote: “{text}”",

        "premium_info": (
            "⭐️ VYBLA+ for {stars} Stars\n\n"
            "• all card designs\n"
            "• no watermark\n"
            "• stats: mode, time, reactions\n"
            "• feed priority\n\n"
            "Honestly: senders stay anonymous. We don't sell a fake 'guess who' — "
            "that's a scam and a ban risk. Real features only."
        ),
        "premium_already": "You already have VYBLA+ ⭐️ Thank you!",
        "btn_buy_premium": "Buy for {stars} Stars",
        "reveal_honest": (
            "VYBLA keeps senders anonymous by design 🖤\n"
            "We literally don't reveal who wrote, and we won't invent fake hints. "
            "But VYBLA+ gives all designs and stats — hit ⭐️ Premium."
        ),
        "pay_title": "VYBLA+",
        "pay_desc": "All designs, no watermark, stats.",
        "pay_success": "Done! VYBLA+ activated ⭐️🖤",

        "self_note": "(this is your own link, but ok — write to yourself)",
    },
}


def t(lang: str, key: str, **kw) -> str:
    lang = "en" if lang == "en" else "ru"
    template = TEXTS.get(lang, TEXTS["ru"]).get(key) or TEXTS["ru"][key]
    return template.format(**kw) if kw else template


def lang_of(language_code: str | None) -> str:
    return "en" if (language_code or "").lower().startswith("en") else "ru"
