# Telegram-бот предложки «Подслушано Измайлово» (масштабированная версия)

Бот на **aiogram 3** (long polling). Принимает анонимные предложения и сообщения для админов, копирует их в закрытую админ-группу и позволяет админам отвечать пользователям.

Добавлено:
- ✅ Команды меню (`/start`, `/suggest`, `/contact`, `/stats`) — кнопка «Меню» в поле ввода
- ✅ Health-check сервер (aiohttp) для Render/Railway
- ✅ Telegram Mini App (FastAPI + SQLite) с рейтингом и анонимностью
- ✅ Подготовка к деплою на Render (Background Worker) и Railway

## 📁 Структура проекта

```
tg_suggestion_bot/
├── bot.py              # Бот: хендлеры, FSM, команды меню, WebApp-кнопка
├── db.py               # SQLite (aiosqlite): основные таблицы + статистика + профили
├── texts.py            # Все тексты сообщений
├── config.py           # Централизованная конфигурация из .env
├── main.py             # Точка входа: бот + health-check + FastAPI вместе
├── web_server.py       # aiohttp health-check (для Render/Railway)
├── fastapi_app.py      # FastAPI бэкенд Mini App (валидация initData, топ, профили)
├── static/
│   ├── index.html      # Фронтенд Mini App
│   ├── style.css       # Стили
│   └── app.js          # Логика Mini App (Telegram WebApp SDK)
├── .env.example        # Пример переменных окружения (без секретов)
├── .env                # Создаётся вручную из .env.example (секреты, не коммитится)
├── .gitignore          # Исключения для Git
├── requirements.txt    # Зависимости Python
├── render.yaml         # Конфигурация Render
├── Procfile            # Конфигурация Railway/Heroku
└── README.md
```

## 🚀 Задача 1 — Хостинг (Render / Railway)

### 1. Подготовка проекта к деплою

#### Шаг 1. Создайте репозиторий на GitHub

1. Зайдите на [GitHub](https://github.com) и создайте новый репозиторий (например, `tg-suggestion-bot`).
2. Склонируйте его локально:
   ```bash
   git clone https://github.com/ВАШ_ЛОГИН/tg-suggestion-bot.git
   cd tg-suggestion-bot
   ```
3. Скопируйте все файлы из этой папки в клонированный репозиторий.

#### Шаг 2. Настройте `.gitignore`

Файл `.gitignore` уже создан — он исключает `__pycache__`, `.env`, `*.db`, `.vscode` и другое. Секреты никогда не попадут в Git.

#### Шаг 3. Вынесите токены в переменные окружения

Скопируйте `.env.example` в `.env` и заполните реальными значениями:

```env
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
ADMIN_CHAT_ID=-1001234567890
CHANNEL_LINK=https://t.me/your_channel
MINI_APP_URL=https://your-app.onrender.com   # будет получено после деплоя FastAPI
PORT=8080
```

> **Важно:** `.env` добавлен в `.gitignore` и не должен попадать в репозиторий. На хостинге переменные задаются через панель управления (Environment Variables).

### 2. Деплой на Render (рекомендуется)

Render позволяет запустить бота как **Background Worker** — он работает 24/7 и не засыпает.

#### Шаг 1. Загрузите код на GitHub

```bash
git add .
git commit -m "Initial commit: scaled bot with Mini App"
git push origin main
```

#### Шаг 2. Создайте Web Service на Render

1. Зайдите на [Render Dashboard](https://dashboard.render.com).
2. Нажмите **New +** → **Web Service**.
3. Подключите ваш GitHub-репозиторий.
4. Настройки:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Instance Type:** Free (или Starter для большей стабильности)

#### Шаг 3. Добавьте переменные окружения

В разделе **Environment Variables** добавьте:
- `BOT_TOKEN` — токен от BotFather
- `ADMIN_CHAT_ID` — ID админ-группы (отрицательное число)
- `CHANNEL_LINK` — ссылка на ваш канал
- `MINI_APP_URL` — будет заполнено позже (ссылка на FastApp)
- `PORT` — `8080`

#### Шаг 4. Health-check

Render требует, чтобы сервис отвечал на HTTP-запросы. Наш `web_server.py` запускает aiohttp-сервер на порту `PORT` (по умолчанию 8080) и обрабатывает `GET /` и `GET /health`.

Render автоматически определяет порт через переменную `PORT`, но мы жестко задаём `0.0.0.0:PORT` в коде.

#### Шаг 5. После деплоя

1. Скопируйте URL вашего сервиса Render (например, `https://tg-suggestion-bot.onrender.com`).
2. Это URL станет `MINI_APP_URL` для Mini App.
3. Обновите переменную `MINI_APP_URL` в Render (или в `.env` локально).
4. Перезапустите сервис.

> **Примечание:** Бесплатный тариф Render может «засыпать» после 15 минут без активности. Чтобы бот работал 24/7, используйте платный тариф или настройте внешний пинг (например, через Cron Job на cURL к `https://ваш-сервис.onrender.com/health` каждые 10–14 минут).

### 2. Деплой на Railway (альтернатива)

Railway также поддерживает Python и не засыпает на платном тарифе ($5/мес).

1. Зайдите на [Railway](https://railway.app).
2. Создайте новый проект → **Deploy from GitHub repo**.
3. Выберите ваш репозиторий.
4. Railway автоматически найдёт `Procfile` (`worker: python main.py`).
5. Добавьте переменные окружения в панели Railway: `BOT_TOKEN`, `ADMIN_CHAT_ID`, `CHANNEL_LINK`, `MINI_APP_URL`, `PORT`.
6. Деплой начнётся автоматически.

## 📱 Задача 2 — Удобное меню ввода (без /start)

### Что сделано:

1. **`set_my_commands`** в aiogram 3 — при старте бота настраиваются команды:
   - `/start` — 👋 Главное меню
   - `/suggest` — 📝 Отправить предложение
   - `/contact` — 💬 Связаться с админами
   - `/stats` — 📊 Статистика и рейтинг

   Пользователь видит кнопку **«Меню»** слева от поля ввода и может выбрать любую команду.

2. **`/suggest`** — сразу переводит пользователя в FSM-состояние `waiting_for_suggestion`, без повторного вывода приветственного текста. Пользователь сразу приступает к вводу предложения.

3. **`/contact`** — сразу переводит в состояние `waiting_for_admin_message` для связи с админами.

4. **Обновлённый `fallback`** — если пользователь пишет без команды, бот подскажет использовать `/suggest`, `/contact` или `/start`.

## 🏆 Задача 3 — Telegram Mini App (рейтинги, статистика, анонимность)

### Логика работы:

1. Пользователь нажимает кнопку **«📊 Статистика»** в боте или команду `/stats`.
2. Открывается Mini App по URL из `MINI_APP_URL`.
3. При первом заходе — экран выбора: «Остаться анонимным» или «Указать никнейм».
4. После выбора — таблица лидеров (Топ-10) с никнеймами или «Аноним».
5. Данные берутся из SQLite (`user_stats`, `user_profiles`).

### Бэкенд (FastAPI):

- `GET /api/leaderboard` — топ пользователей по количеству предложений.
- `POST /api/profile/save` — сохранение ника / анонимности (с валидацией `initData`).
- `GET /api/profile/me` — получение профиля текущего пользователя.
- Валидация `initData` через HMAC-SHA256 с токеном бота (защита от подделки).

### База данных:

Новые таблицы:
- `user_stats` — `user_id`, `suggestions_count`
- `user_profiles` — `user_id`, `display_name`, `is_anonymous`, `updated_at`

При каждом успешном предложении вызывается `db.increment_suggestion_count(user_id)`.