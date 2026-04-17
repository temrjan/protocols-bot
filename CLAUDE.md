# CLAUDE.md — онбординг для Claude Code

Этот файл — полный вводный брифинг для Claude в новой сессии. Прочитав его,
ты должен понимать стек, архитектуру, принятые решения, правила и как
безопасно вносить изменения. Если что-то из перечисленного здесь противоречит
коду — доверяй коду и обнови этот файл.

## Что это за проект

Telegram-бот **protocols-bot**, выдаёт PDF/JPG-протоколы испытаний
аптекам и принимает загрузки новых протоколов/документов от модераторов.
Продакшн живой, пользователи — сеть аптек, продукт — БАДы Bifolak/
Bifolak Neo/Dermacomplex и т. п. Заказчик — `temrjan`.

## Стек

| Слой | Технология |
|------|------------|
| Bot framework | aiogram 3.22 |
| Runtime | Python 3.11, uvloop |
| БД | SQLite через aiosqlite (один коннект, сериализованные запросы) |
| FSM storage | Redis (db=1) с fallback на MemoryStorage |
| Config | Pydantic Settings v2 (`.env` файл) |
| Logging | loguru (stderr → journalctl + файл `logs/bot.log`) |
| Storage | Локальная ФС в `$STORAGE_ROOT` |
| Lint/format | ruff (конфиг в `ruff.toml`) |
| Tests | pytest (smoke-уровень) |
| CI/CD | GitHub Actions: lint + pytest → SSH deploy |

## Структура

```
bot/
├── __main__.py            # entrypoint: polling, middlewares, routers, error handler
├── core/
│   ├── config.py          # Settings (Pydantic), читает .env
│   ├── loader.py          # Bot, Dispatcher, выбор FSM storage
│   ├── logging.py         # setup_logging — loguru на stderr + файл
│   └── products.py        # PRODUCT_NAMES — канонический список препаратов
├── database/
│   ├── __init__.py        # Database: connect/close, CREATE TABLE IF NOT EXISTS
│   ├── models.py          # Protocol, Moderator, User, Document (dataclasses)
│   └── repositories/      # BaseRepository + 4 repo-класса (SQL параметризован)
├── handlers/
│   ├── common.py          # /start, /cancel, выбор языка, reply-fallback
│   ├── download.py        # скачивание протокола (кэш tg_file_id)
│   ├── admin/             # upload протокола, upload документа, модераторы
│   └── user/              # filters, search, documents, menus (shared-flows)
├── keyboards/             # inline + reply билдеры
├── middlewares/           # database (инъекция repos), throttling, logging
├── services/              # StorageService (save_bytes/get_path/exists)
├── states/                # FSM StatesGroup'ы (upload, search, filters, admin)
└── utils/
    ├── __init__.py        # slugify, protocol_storage_key, safe_send_many, chunk
    ├── text.py            # TEXT словарь + get_text (общая локализация)
    └── protocol.py        # format_protocol_text, send_protocol_list, format_size
```

Легаси `app/` удалён — сервис давно поднят через `python -m bot`.

## Архитектура и принятые решения

### Слои
Thin handler → service (где есть) → repository → SQLite. Business-logic
в handler допустима: проект небольшой (до 10 handler-ов на раздел),
god-классы явно запрещены в стандартах, но и over-abstractions тоже.

### FSM storage: Redis с fallback
`bot/core/loader.py:build_storage` возвращает `RedisStorage` если задан
`REDIS_URL`, иначе `MemoryStorage` + warning. На старте бот пингует
Redis в `__main__.verify_fsm_storage`; если пинг упал — storage тихо
подменяется на MemoryStorage, polling продолжается. Причина: FSM-state
терялся при каждом CD-деплое, модераторы в середине upload-флоу
теряли прогресс. На проде `REDIS_URL=redis://localhost:6379/1` (db=1,
чтобы не конфликтовать с другими aiogram-ботами в db=0).

### Middleware-порядок (зарегистрирован в `__main__.main`)
1. `LoggingMiddleware` — на message и callback_query.
2. `ThrottlingMiddleware(rate_limit=1.0)` — отдельные экземпляры на
   `dp.message` и `dp.callback_query`. Кулдауны независимы. При throttle
   callback мы вызываем `event.answer()`, чтобы снять часики на кнопке.
3. `DatabaseMiddleware` — инъекция `protocol_repo`, `moderator_repo`,
   `user_repo`, `document_repo` в kwargs handler-а.

`storage_service` лежит в `dp["storage_service"]` и достаётся handler-ами
по имени.

### Глобальный error handler
`@dp.errors()` в `__main__.global_error_handler`: логирует traceback,
шлёт пользователю двуязычное «Произошла ошибка. Попробуйте позже.»
(best-effort через `contextlib.suppress`), подтверждает callback чтобы
убрать часики, возвращает True. Любой bug в handler-е не может уронить
polling loop.

### Кэш tg_file_id
У `protocols` и `documents` есть колонка `tg_file_id`. При первой отдаче
файла сохраняем id, повторные клики уходят на Telegram-серверный кэш
(мгновенно). Если id устарел — `answer_photo`/`answer_document` кидает
`TelegramBadRequest`; handler (`bot/handlers/download.py` и
`bot/handlers/user/documents.py`) ловит **только** этот класс, зануляет
`tg_file_id` в БД и падает fallthrough в ветку загрузки из локального
storage. Сетевые ошибки не приводят к инвалидации.

### callback_data безопасность
Telegram ограничивает callback_data 64 байтами. Категории документов
на кириллице легко превышают лимит. Поэтому используем индексный
формат: `doc_cat:<idx>`, в handler повторно зовём `get_categories()` и
резолвим по индексу. Стабильная сортировка `ORDER BY category COLLATE
NOCASE ASC` гарантирует согласованность между показом и кликом.

### Массовая отправка
`bot.utils.safe_send_many` — помощник для отправки множества сообщений
в цикле (список протоколов, список документов). Держит 50 мс паузу,
ловит `TelegramRetryAfter` и делает один ретрай после `sleep(retry_after)`.
Без него Telegram режет сообщения после ~30 подряд на чат.

### FSM и фильтры
На `F.document` и `F.photo` в `admin/upload.py` стоит `StateFilter(None)` —
иначе они перехватывали бы файлы, отправленные посреди чужого FSM-флоу
(например, во время ожидания номера протокола).

### Права
- Primary admin — первый ID из `ADMINS` env. Имеет `/admin` и может
  загружать документы, назначать модераторов.
- Moderator — в таблице `moderators` БД (или сам primary admin).
  Может загружать протоколы.
- Rights проверяются inline в handler-ах (через
  `moderator_repo.is_moderator`). Filter-классы `IsAdmin`/`IsModerator`
  удалены — не использовались.

## Правила кода

- Python 3.11+, type hints **обязательны** на сигнатурах функций.
- Google docstrings для публичных функций и классов.
- `async/await` для любого I/O. Блокирующие операции (fs, PIL) — через
  `asyncio.to_thread`.
- SQL — только параметризованный (`?` или `:name`), никогда f-string.
- Узкие `except` (`sqlite3.IntegrityError`, `TelegramBadRequest`,
  `TelegramRetryAfter`) — widespread `except Exception` допустим только
  как last-resort с логированием.
- `loguru`, не `print`. Логи шаблонами: `logger.info("x={}", x)`, не
  f-string (так теряется intended структура).
- `contextlib.suppress(Exception)` — для cosmetic ops (убрать клавиатуру,
  удалить сообщение), которые не критичны.
- Никаких emoji в кодовых комментариях и commit-сообщениях, если
  пользователь явно не попросил.
- Не добавляй комментарии, которые дублируют имя функции. Комментарии
  нужны только для WHY (хотфиксы, нетривиальные инварианты).

## Git и деплой

- **Trunk-based**: основная ветка `main`. Фича или фикс = feature-branch.
- **Один фикс = один PR.** Имена веток: `fix/`, `feat/`, `refactor/`,
  `chore/`, `docs/`, `test/`.
- **Conventional commits**: `fix: ...`, `feat: ...`, `refactor: ...` и т. п.
- **CI** (`.github/workflows/ci.yml`): `ruff check bot/`, `ruff format
  --check bot/`, `pytest tests/ -v` с фейковым `BOT_TOKEN` в env.
- **CD** (тот же workflow, job `deploy`): при `push` в `main` заходит по
  SSH на `biotact-main`, делает `git fetch` + `git reset --hard
  origin/main` (важно: сбрасывает локальные изменения на сервере, если
  кто-то правил .env — они НЕ трогаются), `pip install -r
  requirements.txt`, `systemctl restart protocols-bot.service`.
- **Секреты**: `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`,
  `DEPLOY_PORT` в GitHub Secrets.

## Воркфлоу задачи

```
Изучи → План → /check → Исправь → /codex → Реализуй → Diff → Коммит
```

Каждый этап отдельным сообщением, коммит на каждой значимой точке.
Сложные задачи бьются на атомарные PR.

## Типовые операции

### Прочитать логи сервиса

```bash
ssh biotact-main "journalctl -u protocols-bot.service -f"
ssh biotact-main "journalctl -u protocols-bot.service --since '1 hour ago' --no-pager"
```

### Посмотреть статус

```bash
ssh biotact-main "systemctl status protocols-bot.service --no-pager"
```

### Перечитать `.env` после ручной правки на сервере

```bash
ssh biotact-main "systemctl restart protocols-bot.service"
```

### Заглянуть в БД на проде

```bash
ssh biotact-main "cd /opt/bots/protocols-bot && .venv/bin/python3 -c '
import sqlite3
c = sqlite3.connect(\"storage/protocols.db\")
for r in c.execute(\"SELECT * FROM protocols LIMIT 5\"): print(r)
'"
```

### Redis keys проверить

```bash
ssh biotact-main "redis-cli -n 1 KEYS '*' | head"
```

## Известные ограничения

- **Нет миграций БД**. Схема создаётся через `CREATE TABLE IF NOT
  EXISTS`. Любое изменение колонки требует ручного ALTER на проде или
  осознанной миграции — обсудить с пользователем перед изменениями.
- **SQLite один connection**. Длинные транзакции (большой upload)
  блокируют других. Для текущих нагрузок ок.
- **Тесты только smoke** (`test_imports.py`, `test_config.py`).
  Function-level тестов handler-ов нет. Регрессий ловим через прод-логи.
- **Deploy на root**. Service запускается под root. Вне scope текущих
  задач, но при аудите безопасности этот пункт висит.
- **No healthcheck endpoint**. Liveness проверяется через `systemctl
  is-active` (грубо — процесс жив). Deep health (polling активен, БД
  доступна) нет.

## Чего НЕ делать

- Не использовать `git add -A` — .claude/, ai-architecture-*, .env
  могут случайно попасть в коммит. Всегда по имени.
- Не пушить прямо в `main` — только через PR.
- Не править продовый код/`.env` по SSH напрямую. Все изменения кода
  идут через репозиторий и CD.
- Не трогать `.env.example` без синхронного обновления сервера, если
  добавляешь обязательную переменную.
- Не менять схему БД без миграции и подтверждения пользователя.
- Не удалять файлы/таблицы/пользователей без явного подтверждения.
- Не использовать `git commit --amend` после push и не делать
  force-push в `main`.
- Не коммитить `logs/`, `storage/`, `.venv/`, `.env` (они в `.gitignore`;
  если нет — добавить перед коммитом).

## Справочные точки

- `C:\Claude\codex\standards\` — внешние стандарты (architecture.md,
  pipeline.md, python.md, telegram-bot.md). Актуальны для всего
  temrjan-стека. Загружаются скиллом `/codex`.
- `~/.claude/CLAUDE.md` — глобальные правила Claude-пользователя.
- MCP серверы пользователя: github, context7, sequential-thinking,
  playwright, firecrawl, youtube-transcript, Gmail/Calendar/Drive.

## Контакты и ownership

- Репозиторий: `github.com/temrjan/protocols-bot`, ветка `main`.
- GitHub CLI аутентифицирован как `temrjan`, SSH protocol.
- Server SSH key: `~/.ssh/claude_migration` (алиас `biotact-main`).
- Основной контакт — пользователь Claude-сессии.
