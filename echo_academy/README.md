# ECHO Academy Bot

Telegram-бот онлайн-школы: роли admin / traffer / teacher / student, лиды, сделки, доли, выплаты.

Стек:
- **Бот** — aiogram 3 → деплой на [Render](https://render.com)
- **БД** — [Supabase](https://supabase.com) (Postgres)
- **Mini App / лендинг** — GitHub Pages (`index.html`)

---

## Быстрый старт (локально)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# заполни BOT_TOKEN и ADMIN_ID
python -m bot.main
```

Без `DATABASE_URL` используется локальный `echo.sqlite` (только для разработки).

---

## 1. Supabase

1. Создай проект на supabase.com
2. **Project Settings → Database → Connection string → URI**
3. Скопируй URI (лучше **Transaction pooler**, порт `6543`)
4. Вставь в `.env` / Render env как `DATABASE_URL`

Пример:
```
DATABASE_URL=postgresql://postgres.xxxx:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

Код сам подставит драйвер `asyncpg`.  
При первом запуске `init_db()` создаст таблицы `users`, `courses`, `leads`, `deals` и засеет 3 курса.

---

## 2. Render

### New → Web Service → Connect GitHub repo

| Параметр | Значение |
|----------|----------|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python -m bot.main` |

### Environment Variables

| Key | Value |
|-----|--------|
| `BOT_TOKEN` | токен от BotFather |
| `ADMIN_ID` | твой Telegram ID |
| `DATABASE_URL` | URI из Supabase |
| `BOT_MODE` | `polling` (проще) или `webhook` |
| `WEBHOOK_HOST` | `https://YOUR_SERVICE.onrender.com` (только для webhook) |
| `WEBHOOK_PATH` | `/webhook` |
| `WEBHOOK_SECRET` | любая строка (опционально) |
| `PORT` | Render подставит сам |

**Polling** — работает сразу, без публичного URL.  
**Webhook** — поставь `BOT_MODE=webhook` и `WEBHOOK_HOST` на URL сервиса Render.

Free tier Render засыпает без трафика — для webhook это неудобно, polling на free тоже может тормозить. Для прода лучше paid instance или другой хост.

---

## 3. GitHub Pages (Mini App)

`index.html` — лендинг. Подключи как GitHub Pages:

1. Settings репо → Pages → Source: Deploy from branch → `main` / root (или `/docs`)
2. В BotFather: `/newapp` → укажи URL Pages

Пока это маркетинг-страница. Связка с ботом (оплата, личный кабинет) — следующий этап.

---

## Роли

| Роль | Как выдать |
|------|------------|
| admin | `ADMIN_ID` в env или `/role <id> admin` |
| traffer / teacher / student | `/role <telegram_id> traffer` (только admin) |

---

## Структура

```
echo_academy/
├── bot/
│   ├── main.py          # polling / webhook
│   ├── config.py        # env
│   ├── database.py      # модели + бизнес-логика
│   ├── filters.py
│   ├── keyboards.py
│   ├── states.py
│   └── handlers/
├── index.html           # Pages / Mini App
├── requirements.txt
├── .env.example
└── README.md
```

---

## Важно

- **Не коммить `.env`** — токен и пароль БД только в Render / локально.
- Старый токен из архива лучше **перевыпустить** в BotFather.
- Платежи пока mock — реальную кассу добавим отдельно.
