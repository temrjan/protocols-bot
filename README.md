# protocols-bot

Telegram-бот для выдачи PDF/JPG-протоколов испытаний аптекам и загрузки новых
протоколов и сопроводительных документов модераторами.

Стек: **aiogram 3.22 + Python 3.11 + aiosqlite + Redis FSM + loguru**.

## Возможности

- Поиск протокола по номеру, по году+номеру или по названию препарата.
- Фильтр: год → препарат → список.
- Дополнительные документы (регистрационные, декларации и т. п.) по категориям.
- Загрузка протоколов (PDF/JPG) модераторами, загрузка документов админом.
- Кэш `tg_file_id` для мгновенной повторной выдачи файлов.
- Двуязычный интерфейс: русский и узбекский.

## Быстрый старт (локально)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # заполнить BOT_TOKEN, ADMINS и пути
python -m bot
```

## Переменные окружения

| Переменная | Обязательно | Описание |
|------------|:-----------:|----------|
| `BOT_TOKEN` | да | Токен бота от BotFather |
| `ADMINS` | да | Список Telegram ID через запятую. Первый — primary admin (доступ к `/admin`) |
| `DB_PATH` | да | Путь к SQLite-файлу |
| `STORAGE_ROOT` | да | Корень локального файлового хранилища |
| `STORAGE_MODE` | — | `local` (по умолчанию) |
| `REDIS_URL` | — | `redis://host:port/db`. Если не задан — используется in-memory FSM (state теряется на рестарте) |
| `LOG_LEVEL` | — | `INFO` по умолчанию |
| `DEBUG` | — | `false` по умолчанию |

## Деплой в прод

CI/CD через GitHub Actions: любой push/merge в `main` → lint + pytest →
SSH deploy на `biotact-main` → `systemctl restart protocols-bot.service`.

Ручные шаги на сервере нужны только при новых env-переменных — править
`/opt/bots/protocols-bot/.env` и делать `systemctl restart`.

## Серверная информация

- Host: `biotact-main` (`95.111.224.251:2222`)
- Путь: `/opt/bots/protocols-bot`
- Сервис: `protocols-bot.service` (`Restart=always`, `RestartSec=10`)
- Логи: `journalctl -u protocols-bot.service -f` + файл `logs/bot.log`
  (ротация 10 МБ, хранение 14 дней).
- Redis: локальный, `db=1` (изолирован от других ботов на том же инстансе).

## Управление модераторами

- Primary admin (первый ID в `ADMINS`) отправляет `/admin` → «Назначить
  модератора» → вводит Telegram ID. Модератор может загружать протоколы;
  загружать документы может только primary admin.

## Разработка

Гайд для работы в этом репозитории — в `CLAUDE.md`.

```bash
ruff check bot/            # lint
ruff format --check bot/   # format
pytest tests/ -v           # tests
```

Комментарий: локальный прогон `pytest` требует установленных зависимостей
(aiogram, pydantic и т. д.) — лучше всего из активированного `.venv`.
