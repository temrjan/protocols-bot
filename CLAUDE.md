# ProtocolsBot — Telegram Bot for Protocol Distribution

## Stack

| Component | Tech |
|-----------|------|
| Bot | aiogram 3.22 + Python 3.11 |
| Database | SQLite (aiosqlite) |
| Config | Pydantic Settings v2 |
| Logging | loguru |
| Storage | Local filesystem |

## Structure

```
bot/               # Main bot (modular, preferred)
├── core/          # Config, loader, logging
├── database/      # Models + repositories
├── handlers/      # Telegram handlers (common, user/, admin/)
├── keyboards/     # Inline + reply keyboards
├── middlewares/    # DB, logging, throttling
├── services/      # Storage, protocol logic
├── states/        # FSM states
└── utils/         # Helpers

app/               # Legacy monolithic bot (deprecated, do not modify)
tests/             # Tests
```

## Commands

```bash
# Lint
ruff check bot/
ruff format --check bot/

# Test
pytest tests/ -v

# Run locally
python -m bot
```

## Server

- Host: biotact-main (95.111.224.251:2222)
- Path: /opt/bots/protocols-bot
- Service: systemctl (protocols-bot.service)
- Deploy: git pull → pip install → systemctl restart

## Rules

- Follow Codex standards (~/Codex/standards/)
- Type hints mandatory on all functions
- No print() — use loguru logger
- No hardcoded secrets — use .env
- Async/await for all I/O
- Do NOT modify app/ — it's legacy, use bot/
