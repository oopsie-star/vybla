# BotFather setup

Send these to @BotFather.

**/setabouttext** (max 120 chars):
```
Твоя личная ссылка на правду. Узнай как тебя видят на самом деле.
```

**/setdescription**:
```
VYBLA — твое зеркало. Создаешь ссылку, кидаешь в био и получаешь честные анонимные вайбы на красивых карточках для сторис. Комплименты, ред флаги, краши.
```

**/setuserpic** — upload your VYBLA logo.

**Payments:** Telegram Stars (XTR) need no separate provider token — `send_invoice(currency="XTR")` works out of the box. Just make sure the bot is allowed to receive payments (it is by default for Stars).

**Privacy for groups:** not required — VYBLA works in private chat only.

> ⚠️ Rotate the bot token via **/revoke** if it was ever pasted in plaintext, then update `.env`.
