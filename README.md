# ProtocolsBot

Минимальный продакшн-готовый Telegram-бот для выдачи PDF/JPG-протоколов аптекам и загрузки новых протоколов администраторами.

## Быстрый старт
1. Перейдите в каталог проекта: `cd /opt/protocols-bot`.
2. Заполните `.env` на основе `.env.example`:
   - `BOT_TOKEN`
   - `DB_PATH`
   - `STORAGE_MODE`, `STORAGE_ROOT`
   - `ADMINS` — список Telegram user_id администраторов.
3. При необходимости обновите зависимости: `.venv/bin/pip install -r requirements.txt`.
4. Подготовьте базу данных: `bash scripts/db_provision.sh`.
5. Запустите сервис: `sudo systemctl restart protocols-bot.service`.

## Локальный прогон
```
source /opt/protocols-bot/.venv/bin/activate
python -m app.main
```

Проект использует SQLite-файл, хранящийся в `STORAGE_ROOT`.

## Управление сервисом
- Просмотр логов: `journalctl -u protocols-bot.service -f`
- Перезапуск: `systemctl restart protocols-bot.service`
- Остановка: `systemctl stop protocols-bot.service`
- Статус: `systemctl status protocols-bot.service`

Логи приложения пишутся в `logs/bot.log` (ротация 10 МБ, хранение 14 дней).

Чтобы загрузить новый протокол админ отправляет PDF или JPG в чат бота, после чего бот спрашивает год (есть быстрые кнопки с актуальным годом), название препарата и номер протокола.

Поиск протокола поддерживает ввод только номера («01») или связки «ГГГГ Номер» (например, «2025 01»).

## Обновление
1. `cd /opt/protocols-bot`
2. `git pull`
3. `.venv/bin/pip install -r requirements.txt`
4. `systemctl restart protocols-bot.service`

## Бэкап
- Перед крупными изменениями: `git status` → `git commit` → при необходимости архивируйте каталог: `tar czf protocols-bot-$(date +%Y%m%d%H%M).tar.gz /opt/protocols-bot`.

## Добавление администраторов
- Обновите `ADMINS` в `.env` (через запятую без пробелов или с пробелами — не принципиально).
- Выполните `systemctl restart protocols-bot.service`, чтобы переменные окружения перечитались.

## Назначение модераторов
- Основной администратор (первый ID в `ADMINS`) отправляет боту команду `/admin` и выбирает кнопку «Назначить модератора».
- В ответ введите Telegram ID пользователя (числом) — после этого он сможет загружать PDF/JPG-файлы протоколов.

## Настройка списка препаратов
- В файле `app/bot.py` отредактируйте константу `PRODUCT_NAMES`, перечислив доступные названия. При загрузке протокола модератор выбирает препарат именно из этого списка.
