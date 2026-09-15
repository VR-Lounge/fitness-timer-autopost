# fitness-timer-autopost

Автоматический постинг релевантных фото+текстов в Telegram канал и на сайт TabataTimer.

## 🎯 Главная идея

**1 источник → 3 публикации:**

1. **Парсинг источника** (например, `https://skinnyms.com/slow-cooker-thick-chunky-beef-stew-recipe/`)
   - Извлекается статья с текстом и всеми изображениями
   
2. **Рерайтинг через DeepSeek AI**
   - Создаётся короткий текст для Telegram (900 символов)
   - Создаётся расширенный текст для полноценной статьи (2000-4000 символов)
   
3. **Три публикации создаются одновременно:**
   - ✅ **Пост в Telegram** (`@fitnesstimer`) - фото + короткий текст
   - ✅ **Пост в blog-posts.json** - сохраняется для отображения на сайте
   - ✅ **HTML страница** (`/blog/[slug].html`) - полноценная статья со всеми фото

**Важно:** Все 3 публикации про одну и ту же тему, из одного источника, с одинаковыми изображениями.

---

## 📌 Центральная инструкция: откуда берутся статьи и какие картинки где должны быть

Этот раздел — **опорная памятка** для разработки и деплоя: чтобы превью ленты, модалка и шапка статьи не расходились с смыслом текста (еда vs тренировки).

### Как образуется статья на сайте (цепочка)

1. Парсер (`skinnyms_parser.py`, парсеры WH/MH и т.д.) формирует объект поста: текст, теги, `source`, массив `images[]`, черновик `image`.
2. Данные пишутся в **`public_html/blog-posts.json`** (единый источник для ленты `blog.html`).
3. **`generate_blog_post_page.py`** строит для каждого поста HTML в **`public_html/blog/[slug].html`**, подставляет Open Graph, галерею, выбирает **главное фото статьи (hero)**. В начале полного прогона скрипт **сразу переписывает** `blog-posts.json`: для рецептных постов выставляет **`image`** и порядок **`images[]`** по той же эвристике, что и hero в HTML — чтобы лента и модалка не зависели от «ручного» порядка после парсера.
4. **`public_html/blog.html`** (клиентский JS) читает `blog-posts.json` и рисует карточки, модалку; для hero превью вызывается **`pickHeroImageForPost`** — логика должна совпадать с Python по смыслу.

Без шага загрузки на Object Storage пользователи видят **старую** копию JSON/HTML на `www.tabatatimer.ru`. Это не «откат кода в репозитории», а **необновлённый бакет**.

### Рецепты / еда / диеты (контент про блюда)

**Когда это «рецептный» пост для выбора фото**

- `id` начинается с **`recipes_`** или **`skinnyms_recipes_`** (так помечается пайплайн «Рецепты и питание» в `womenshealth_parser.py` / skinnyms), **или**
- `source` = `recipes` или `skinnyms_recipes`, **или**
- в тегах есть **«рецепт»** / **«рецепты»**.

Префикс `id` нужен, чтобы даже при устаревшем или перезаписанном `source` в JSON hero оставался «еда», а не сток из зала.

Не полагайтесь только на теги «питание» / «диеты» для переключения на «фото еды»: статьи про режим питания при тренировках могут оставаться с **фитнес-hero** — для них действует обычная логика не-рецепта.

**Что должно быть на картинке**

- В превью ленты, в модалке и в **шапке статьи** — **фото блюда** (или напитка/готовой порции), в том же смысле, что и первая иллюстрация рецепта в галерее внизу страницы.
- Типичное имя файла с сайта рецептов: `skinnyms_recipes_<id>_0_<hash>_<English-Dish-Name>.jpg` — индекс **`_0_`** и **название блюда** в имени файла — хороший признак «правильного» кадра.
- То же для пайплайна без префикса `skinnyms_` в имени файла: **`recipes_<id>_0_<hash>_...jpg`** (в `source` при этом всё равно может быть `recipes`).

**Чего избегать как главного фото рецепта**

- Служебные/стоковые файлы вида **`..._<hash>_123.jpg`** (только цифры перед расширением) — часто это не блюдо, а абстрактный кадр. Это относится и к **`recipes_<id>_*_*_31.jpg`**, не только к `skinnyms_recipes_*`.
- Подписи **alt/title** вроде «Спортивное питание: продукты для энергии…», «фото тренировки и фитнеса» — принудительно **хуже** любого кадра с именем блюда в basename (см. штраф в `_score_recipe_image_for_hero`).
- Локальные стоки **`/images/Fitness/.../Fitness | Woman|Man ...`** — для рецепта **не использовать** как hero.
- Имена загруженных файлов с явными маркерами **тренировки/зала** в slug (например `Woman-Holding-Dumbbells`, `HIIT-Workout`) — штрафуются **даже при `_0_`**, иначе «люди в зале» обходили бы эвристику по индексу.

Логика отбора зашита в **`_score_recipe_image_for_hero`** / **`выбрать_главное_изображение_для_рецепта`** в `generate_blog_post_page.py` и в **`scoreRecipeHeroForImg`** / **`pickHeroImageForPost`** в `blog.html` (меньший числовой score = лучше кандидат). Обе реализации нужно **менять согласованно**.

### Тренировки и мотивация (не рецепт)

- Hero и превью: **люди в зале, тренировка, инвентарь** — нормально, если контент про упражнения/программы.
- Рецептная эвристика **не должна** переключаться только из-за слова «питание» в тегах (см. выше).

### Галерея в конце статьи

- Для skinnyms рецептов в галерею попадают **все** скачанные изображения статьи (см. **`GALLERY_FIX.md`**).
- После выбора hero генератор **переставляет** выбранное фото в начало `images[]` и синхронизирует `post.image`, чтобы лента и модалка брали тот же URL.

### Деплой: без этого «на сайте всё сломано», хотя локально исправлено

После изменения `blog-posts.json`, `blog.html` или HTML статей **обязательно** залить файлы в бакет Yandex Object Storage, иначе на `https://www.tabatatimer.ru/` останется прежняя версия.

- Скрипт: **`upload_blog_to_yandex.sh`** (берёт **`public_html` рядом с папкой `fitness-timer-autopost`**, т.е. актуальный сайт в репозитории «С MediaPipe»; не путать с другой копией `…/TABATATIMER.RU/public_html` на диске). Заливает: `blog-posts.json`, `blog.html`, синхронизация `blog/`, при необходимости `images/blog/`, `sitemap.xml`, `robots.txt`.
- Ручная проверка: скачать `https://www.tabatatimer.ru/blog-posts.json` и убедиться, что у рецептного поста `image` указывает на файл с **`_0_`** / именем блюда, а не на `..._123.jpg`.

### Если случилось X — сделайте Y

| Симптом | Вероятная причина | Действия |
|--------|-------------------|----------|
| В ленте у рецептов снова «люди в зале», локально всё ок | На проде старый **`blog-posts.json`** / **`blog.html`** или деплой шёл **не из того `public_html`** (скрипт брал соседнюю папку уровнем выше) | Перегенерировать (`generate_blog_post_page.py`), убедиться, что **`upload_blog_to_yandex.sh`** использует `С MediaPipe/public_html`, затем снова залить на бакет |
| Шапка статьи не совпадает с первой картинкой галереи | Не прогоняли генератор после смены правил hero | Запустить **`generate_blog_post_page.py`** для всех постов |
| Рецептный пост ведёт себя как тренировка по картинкам | В JSON потерян `source`, нет тега «рецепт» — не сработала эвристика | Убедиться, что `id` вида `recipes_*` / `skinnyms_recipes_*`; перегенерировать блог; проверить парсер |
| Дубликаты статей | Редко дублируются URL или id | Проверить уникальность `id`, `url`, нормализованного заголовка в `blog-posts.json` |
| Пропали недавние посты (на сайте меньше записей, чем в GitHub), тестовый текст у песто | Локальный `blog-posts.json` или бакет перезаписан **урезанной** копией (183 вместо 187 и т.п.) | Взять эталон с **`https://raw.githubusercontent.com/VR-Lounge/tabatatimer-ru/main/blog-posts.json`**, сохранить в `public_html/blog-posts.json`, затем **`generate_blog_post_page.py`** и **`upload_blog_to_yandex.sh`**. Число постов сверить: `len(posts)` в JSON и на проде. |
| «Посты временно недоступны» / пустая лента | `fetch('blog-posts.json')` не выполнился (сеть, блокировка, CORS в автоматизации) | Проверить в обычном браузере; открыть `https://www.tabatatimer.ru/blog-posts.json` напрямую; жёсткое обновление страницы |

### Исключения из рецептного пайплайна

Рецепты **для животных** (печенье для собак и т.п.) не публикуются: фильтр **`recipe_content_filters.blocked_recipe_not_for_humans`** вызывается в `womenshealth_parser.py` (режим `RECIPES_ONLY`) и в `skinnyms_parser.py` для категории рецептов. При добавлении новых шаблонов — расширяйте список в **`recipe_content_filters.py`**.

### SkinnyMS и Cloudflare (GitHub Actions)

`skinnyms.com` отвечает **403 + `cf-mitigated: challenge`** (страница «Just a moment…») с IP датацентров, в том числе runners GitHub Actions. HTML, RSS и даже `wp-content/uploads` недоступны без браузерного challenge — обычные User-Agent/cookies это не обходят.

Поведение пайплайна:

1. **`http_fetch.py`** — browser-like headers, session, retries; при CF challenge хост помечается blocked (soft-skip).
2. **`skinnyms_parser.py`** — один probe; при блоке выходит без ошибки и **не** долбит десятки страниц.
3. **Women's Health** — `SKINNYMS_ONLY=false`, основной рост блога через рабочие RSS (fitnessista, nourishmovelove, sarahfit и др.).
4. **Рецепты** — `RECIPES_ONLY` + fallback **`RECIPES_RSS_FEEDS`** (nutrition/recipe-блоги), без зависимости от SkinnyMS.

### Связанные документы в репозитории

- **`GALLERY_FIX.md`** — почему в галерее все изображения skinnyms и как это связано с hero.
- **`recipe_content_filters.py`** — что не считать «рецептом для людей».
- **`upload_blog_to_yandex.sh`** — актуальный список того, что уезжает на хостинг.
- **`docs/verification-screenshots/`** — эталонные скриншоты продакшена (лента с рецептами, страница статьи с hero-блюдом); см. `README.md` в этой папке.

---

## 📋 Основные ссылки

- **Telegram канал:** https://t.me/s/fitnesstimer
- **Блог на сайте:** https://www.tabatatimer.ru/blog.html
- **GitHub репозиторий (код парсеров и скриптов):** https://github.com/VR-Lounge/fitness-timer-autopost
- **Репозиторий сайта (HTML, `blog-posts.json`, картинки — зеркало для истории):** https://github.com/VR-Lounge/tabatatimer-ru  
  В CI workflow «Рецепты и питание» клонируются **оба**: рядом лежат `fitness-timer-autopost/` и `public_html/`. Генератор и `upload_blog_to_yandex.sh` должны использовать **тот же** `public_html`, что обновляется парсером (соседний каталог), затем объекты заливаются в **бакет** `www.tabatatimer.ru` в Yandex Object Storage — именно оттуда отдаётся прод.
- **Библиотека контента:** `content_library.json`

## 🔄 Как это работает

### Процесс публикации:

1. **GitHub Actions запускает парсеры** (по расписанию или вручную):
   - Women's Health: 4 раза в день (08:00, 12:00, 18:00, 20:00 UTC)
   - Men's Health: по запросу (workflow_dispatch)

2. **Парсеры выполняют:**
   - `skinnyms_parser.py` - парсит skinnyms.com (fitness, recipes)
   - `womenshealth_parser.py` / `menshealth_parser.py` - обрабатывают статьи
   - Фильтруют релевантные статьи (TABATA, HIIT, AMRAP, EMOM, диеты, питание)
   - Проверяют уникальность контента (ФОТО+ТЕКСТ)
   - Делают рерайтинг через DeepSeek AI
   - **Публикуют в Telegram** канал
   - **Сохраняют в `blog-posts.json`**
   - **Генерируют HTML страницы** (`generate_blog_post_page.py`)
   - **Загружают на Яндекс Cloud** (`upload_blog_to_yandex.sh`)

3. **Результат:**
   - Пост появляется в Telegram канале
   - Пост появляется в блоге на сайте
   - Создаётся уникальная HTML страница для SEO
   - Обновляется sitemap.xml

## ⚙️ Настройка GitHub Secrets

### Обязательные секреты:

1. **TELEGRAM_BOT_TOKEN** - токен бота от @BotFather
2. **TELEGRAM_CHAT_ID** - ID канала (`-1003382880193`)
3. **DEEPSEEK_API_KEY** - ключ API от https://platform.deepseek.com/

### Опциональные секреты (для загрузки на Яндекс Cloud):

4. **YANDEX_ACCESS_KEY_ID** - ключ доступа от Yandex Cloud
5. **YANDEX_SECRET_ACCESS_KEY** - секретный ключ от Yandex Cloud

### Как добавить секреты:

1. Перейдите: https://github.com/VR-Lounge/fitness-timer-autopost/settings/secrets/actions
2. Нажмите "New repository secret"
3. Добавьте каждый секрет по отдельности

## 📁 Структура проекта

### Основные файлы:

- `womenshealth_parser.py` - парсер для женского контента
- `menshealth_parser.py` - парсер для мужского контента
- `skinnyms_parser.py` - парсер skinnyms.com
- `generate_blog_post_page.py` - генератор HTML страниц
- `upload_blog_to_yandex.sh` - загрузка на Яндекс Cloud

### Вспомогательные модули:

- `content_uniqueness.py` - проверка уникальности контента
- `image_downloader.py` - скачивание и загрузка изображений
- `image_content_matcher.py` - выбор изображений через DeepSeek
- `fitness_image_collections.py` - коллекции изображений
- `text_cleaner.py` - очистка текста от рекламы
- `telegram_dedup.py` - защита от повторов в Telegram
- `publication_logger.py` - логирование публикаций
- `content_library.py` - библиотека релевантного контента

### Workflows:

- `.github/workflows/recipes-parser.yml` — рецепты и питание (расписание + `workflow_dispatch`): парсеры → `generate_blog_post_page.py` → `upload_blog_to_yandex.sh` → при необходимости коммит в `tabatatimer-ru`
- `.github/workflows/womenshealth-parser.yml` - автоматический парсинг для женщин
- `.github/workflows/menshealth-parser.yml` - парсинг для мужчин (ручной запуск)

## 🚀 Запуск

### Автоматический запуск:

Workflows запускаются автоматически по расписанию или вручную через GitHub Actions UI:
- https://github.com/VR-Lounge/fitness-timer-autopost/actions

### Ручной запуск:

1. Перейдите в Actions
2. Выберите нужный workflow (Women's Health или Men's Health)
3. Нажмите "Run workflow"
4. Выберите ветку (обычно `main`)
5. Нажмите "Run workflow"

## 🔍 Проверка работы

### 1. Проверьте Telegram канал:
- https://t.me/s/fitnesstimer
- Посты должны появляться автоматически
- Формат: ФОТО + ТЕКСТ

### 2. Проверьте блог на сайте:
- https://www.tabatatimer.ru/blog.html
- Посты должны отображаться с фильтрами
- При клике открывается модальное окно с полным текстом

### 3. Проверьте HTML страницы статей:
- https://www.tabatatimer.ru/blog/[slug].html
- Каждая статья имеет уникальную страницу
- Все изображения должны быть загружены

### 4. Проверьте логи GitHub Actions:
- https://github.com/VR-Lounge/fitness-timer-autopost/actions
- Смотрите логи этапа "Запуск парсера Women's Health"

## 🐛 Решение проблем

### Посты не публикуются в Telegram:
1. Проверьте `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` в GitHub Secrets
2. Убедитесь, что бот добавлен в канал как администратор
3. Проверьте логи GitHub Actions

### Посты не появляются в блоге:
1. Проверьте, что `blog-posts.json` обновляется
2. Проверьте, что файлы загружены на Яндекс Cloud
3. Очистите кэш браузера

### HTML страницы не генерируются:
1. Проверьте логи GitHub Actions
2. Убедитесь, что `generate_blog_post_page.py` выполняется
3. Проверьте права доступа к папке `public_html/blog/`

### Файлы не загружаются на Яндекс Cloud:
1. Проверьте секреты `YANDEX_ACCESS_KEY_ID` и `YANDEX_SECRET_ACCESS_KEY`
2. Убедитесь, что у сервисного аккаунта есть права на запись в бакет
3. Проверьте логи GitHub Actions

## 📊 Переменные окружения

### Минимум:
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
DEEPSEEK_API_KEY=...
```

### Опционально:
```
LIBRARY_MAX_ARTICLES=120
LIBRARY_MIN_KEYWORDS=1
LIBRARY_MIN_SCORE=70
LIBRARY_MIN_IMAGES=1
LIBRARY_USE_DEEPSEEK=true
TELEGRAM_ANTI_REPEAT_COUNT=30
PUBLISH_TO_BLOG=true
SKINNYMS_ONLY=true
SKINNYMS_CATEGORIES=fitness,recipes
SKINNYMS_MAX_ARTICLES_PER_RUN=40
```

## ✅ Чеклист перед запуском

- [ ] Все секреты добавлены в GitHub Secrets
- [ ] Telegram бот добавлен в канал как администратор
- [ ] DeepSeek API ключ активен
- [ ] Яндекс Cloud секреты настроены (опционально)
- [ ] Workflows включены в GitHub Actions

## 🎯 Результат

После настройки система будет автоматически:
- ✅ Парсить источники (skinnyms.com, RSS фиды)
- ✅ Фильтровать релевантный контент
- ✅ Проверять уникальность (ФОТО+ТЕКСТ)
- ✅ Делать качественный рерайтинг через DeepSeek
- ✅ Публиковать в Telegram канал
- ✅ Публиковать в блог на сайте
- ✅ Генерировать SEO-оптимизированные HTML страницы
- ✅ Загружать на Яндекс Cloud
- ✅ Обновлять sitemap.xml

**Всё работает автоматически! 🚀**
