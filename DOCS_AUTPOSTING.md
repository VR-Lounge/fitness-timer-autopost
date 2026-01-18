# Автопостинг: краткая инструкция

## Назначение
Система автоматически:
- публикует релевантные посты в Telegram `@fitnesstimer`;
- публикует статьи на сайт `https://www.tabatatimer.ru/blog.html`;
- собирает библиотеку высокорелевантного контента в `content_library.json`.

## Ключевые процессы
1. **Парсинг RSS** → фильтрация релевантных статей.
2. **Парсинг статьи** → извлечение текста + всех изображений (jpg/png/webp/gif и др.).
3. **Рерайт** через DeepSeek.
4. **Анти‑повтор** для Telegram (жёсткий контроль текста и изображения).
5. **Публикация** в Telegram/на сайт по расписанию.
6. **Обновление библиотеки** релевантного контента.

## Переменные окружения
Минимум:
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
DEEPSEEK_API_KEY=...
```

Опционально:
```
LIBRARY_MAX_ARTICLES=120
LIBRARY_MIN_KEYWORDS=1
LIBRARY_MIN_SCORE=70
LIBRARY_MIN_IMAGES=1
LIBRARY_USE_DEEPSEEK=true
TELEGRAM_ANTI_REPEAT_COUNT=30
```

## Где смотреть результат
- **Логи workflow**: этап “Запуск парсера Women's Health”.
- **Блог**: `https://www.tabatatimer.ru/blog.html`.
- **Telegram**: `https://t.me/s/fitnesstimer`.

## Файлы
- `womenshealth_parser.py` — женский парсер и публикации.
- `menshealth_parser.py` — мужской парсер и публикации.
- `content_library.json` — библиотека релевантного контента.
- `telegram_dedup.py` — защита от повторов в Telegram.
