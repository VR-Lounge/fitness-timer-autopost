#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Генератор HTML страниц для статей блога
    
    Создаёт отдельные HTML страницы для каждой статьи с правильными
    мета-тегами, Open Graph, Schema.org для SEO индексации.
    
    Автор: VR-Lounge
"""

import json
import re
import html
from pathlib import Path
from datetime import datetime
from urllib.parse import quote, unquote

# Импортируем функцию загрузки изображений
try:
    from image_downloader import загрузить_все_изображения_блога
except ImportError:
    # Если модуль не найден, создаём заглушку
    def загрузить_все_изображения_блога():
        print("⚠️ Модуль image_downloader не найден, пропускаем загрузку изображений")
        return False

# Путь к файлу с постами
# В GitHub Actions репозиторий клонируется в fitness-timer-autopost, а public_html - отдельно
SCRIPT_DIR = Path(__file__).parent.absolute()
# Проверяем, где мы находимся
REPO_ROOT = None

# В GitHub Actions структура: fitness-timer-autopost/ и public_html/ на одном уровне
if (Path.cwd().parent / 'public_html').exists():
    # Мы в fitness-timer-autopost, public_html на уровень выше (в родительской директории)
    REPO_ROOT = Path.cwd().parent
elif (SCRIPT_DIR.parent / 'public_html').exists():
    # Мы в fitness-timer-autopost, public_html на уровень выше
    REPO_ROOT = SCRIPT_DIR.parent
elif (SCRIPT_DIR / 'public_html').exists():
    # Мы в корне репозитория, public_html внутри
    REPO_ROOT = SCRIPT_DIR
elif (Path.cwd() / 'public_html').exists():
    # public_html в текущей директории
    REPO_ROOT = Path.cwd()
else:
    # Последняя попытка - ищем public_html в родительской директории от текущей
    REPO_ROOT = Path.cwd().parent
    if not (REPO_ROOT / 'public_html').exists():
        # Ещё одна попытка - ищем в родительской директории от SCRIPT_DIR
        REPO_ROOT = SCRIPT_DIR.parent.parent
        if not (REPO_ROOT / 'public_html').exists():
            # Используем текущую директорию как fallback
            REPO_ROOT = Path.cwd()

BLOG_POSTS_FILE = REPO_ROOT / 'public_html' / 'blog-posts.json'
BLOG_POSTS_DIR = REPO_ROOT / 'public_html' / 'blog'
BLOG_POSTS_DIR.mkdir(parents=True, exist_ok=True)

# Мотивационные фразы для заголовка галереи (вместо «Иллюстрации из статьи»).
# Контекст по тегам: Девушкам / Мужчинам / Питание — как на главной (girls-inspiration, men-motivation, nutrition-slider).
MOTIVATION_GIRLS = [
    'Работай тихо, сияй громко.',
    'Ты — дисциплина и свобода.',
    'Хочешь — значит делаешь.',
    'Ты умеешь побеждать себя.',
    'Сильнее. Выше. Увереннее.',
    'Ты — твой главный проект.',
    'Ты прекрасна, когда стараешься.',
    'Твой ритм — твоя сила.',
    'Выбирай себя каждый день.',
]
MOTIVATION_MEN = [
    'Сделай результат неизбежным.',
    'Работай тихо — результат скажет громко.',
    'Сила — это привычка.',
    'Дисциплина важнее мотивации.',
    'Ещё один раунд. Без вариантов.',
    'Держи форму. Держи слово.',
    'Только вперёд.',
    'Слабые ждут. Сильные работают.',
    'Результат любит дисциплину.',
]
MOTIVATION_NUTRITION = [
    'Твоя диета — твой фундамент.',
    'Питание — твоя основа.',
    'Ешь осознанно. Тренируйся регулярно.',
    'Топливо для тела — топливо для побед.',
    'Здоровый выбор каждый день.',
]

# Ключевые слова в alt/title/url — про тренировки/зал (НЕ включать общие фразы про питание из шаблонов alt,
# иначе все картинки рецептов помечаются как «фитнес» и в hero попадает не то фото).
FITNESS_IMAGE_KEYWORDS = (
    'тренировк', 'workout', 'exercise', 'yoga', 'gym', 'pull-up', 'pullup',
    'woman exercising', 'man exercising', 'спортсмен', 'dumbbell', 'гантел', 'штанг',
    'jumping jack', 'plank', 'планк', 'присед', 'squat', 'cardio', 'кардио',
)

# Имена файлов с сайта рецептов часто содержат эти фрагменты (англ. названия блюд)
FOOD_FILENAME_HINTS = re.compile(
    r'recipe|crock|slow-cooker|slow_cooker|dinner|meal|pasta|soup|salad|'
    r'chicken|turkey|beef|fish|smoothie|bowl|cups|lasagna|penne|stew|'
    r'casserole|oatmeal|chips|lettuce|low-carb|lowcarb|keto|bake|skillet|'
    r'instant-pot|multicook|buffalo|taco|wrap|bbq|gumbo|roll|tea|sweet',
    re.I,
)


def url_из_стоковой_фитнес_коллекции(url: str) -> bool:
    """Локальные стоки Fitness | Woman / Fitness | Man — не использовать как hero рецепта."""
    if not url:
        return False
    u = unquote(url).lower().replace('\\', '/')
    if '/images/fitness' in u and ('woman' in u or 'man' in u):
        return True
    return False


def изображение_похоже_на_фитнес(img_dict):
    """True, если изображение скорее про тренировку/сток зала, а не про блюдо."""
    if not img_dict:
        return False
    url = (img_dict.get('url') or '')
    if url_из_стоковой_фитнес_коллекции(url):
        return True
    u_low = unquote(url).lower()
    # Файл скачанного фото рецепта с типичным англ. именем блюда — не считать фитнес-фото
    if '/images/blog/' in url.lower() and FOOD_FILENAME_HINTS.search(u_low):
        return False
    text = ' '.join([
        (img_dict.get('alt') or ''),
        (img_dict.get('title') or ''),
        url,
    ]).lower()
    return any(k in text for k in FITNESS_IMAGE_KEYWORDS)


def _score_recipe_image_for_hero(img_dict):
    """Меньше = лучше кандидат на главное фото рецепта."""
    url = (img_dict.get('url') or '')
    name = unquote(url).split('/')[-1].lower()
    if url_из_стоковой_фитнес_коллекции(url):
        return (3000,)
    if '/images/blog/' not in url.lower():
        return (2000,)
    if FOOD_FILENAME_HINTS.search(name):
        return (0,)
    # типичный паттерн: ..._0_abcd1234_Dish-Name.jpg — низкий индекс вложения
    if re.search(r'_0_[a-f0-9]{6,}_', name, re.I):
        return (1,)
    if re.search(r'_1_[a-f0-9]{6,}_', name, re.I):
        return (2,)
    if re.search(r'_2_[a-f0-9]{6,}_', name, re.I):
        return (3,)
    # короткое имя вида skinnyms_recipes_*_*_65.jpg — часто служебное/не блюдо
    if re.match(r'^skinnyms_recipes_\d+_[a-f0-9]+_\d+\.jpe?g$', name, re.I):
        return (500,)
    if изображение_похоже_на_фитнес(img_dict):
        return (400,)
    return (100,)


def выбрать_главное_изображение_для_рецепта(обработанные_изображения):
    """Hero и превью: сток Fitness | Woman/Man исключаем; приоритет — файлы с именем блюда и индексом _0_."""
    if not обработанные_изображения:
        return None
    scored = sorted(
        обработанные_изображения,
        key=lambda im: _score_recipe_image_for_hero(im),
    )
    best = scored[0]
    # Если лучший всё ещё явный мусор — взять первое не-сток из /images/blog/
    if _score_recipe_image_for_hero(best)[0] >= 400:
        for im in обработанные_изображения:
            u = im.get('url') or ''
            if '/images/blog/' in u.lower() and not url_из_стоковой_фитнес_коллекции(u):
                return im
    return best


def _без_упоминания_источника(текст):
    """Убирает из строки упоминания внутреннего источника (не для публичного контента)."""
    if not текст or not isinstance(текст, str):
        return текст or ''
    текст = re.sub(r'skinnyms_recipes?\s*\|?\s*', 'recipes ', текст, flags=re.I)
    текст = re.sub(r'skinnyms_fitness\s*\|?\s*', 'fitness ', текст, flags=re.I)
    текст = re.sub(r'skinnyms\w*', '', текст, flags=re.I)
    текст = re.sub(r'\s+', ' ', текст).strip()
    return текст if текст else ''


def выбрать_мотивационную_фразу(теги, заголовок):
    """Выбирает мотивационную фразу по контексту статьи (теги). Детерминированно по заголовку."""
    теги_lower = [str(t).strip().lower() for t in (теги or [])]
    if any(t in теги_lower for t in ('питание', 'рецепт', 'рецепты', 'диета', 'еда')):
        список = MOTIVATION_NUTRITION
    elif any(t in теги_lower for t in ('мужчинам', 'мужской', 'мужчины')):
        список = MOTIVATION_MEN
    else:
        список = MOTIVATION_GIRLS  # Девушкам / по умолчанию
    idx = abs(hash(заголовок or '')) % len(список)
    return список[idx]

def очистить_текст_от_html(текст):
    """Очищает текст от HTML тегов для мета-описания"""
    if not текст:
        return ''
    # Убираем HTML теги
    текст = re.sub(r'<[^>]+>', '', текст)
    # Убираем лишние пробелы
    текст = ' '.join(текст.split())
    return текст

SLUG_CACHE = {}
USED_SLUGS = set()
KNOWN_SLUGS = {
    'nutrition_1': 'pravilnoe-pitanie-dlya-trenirovok-chto-est-do-i-po',
    'mens_workout_1': 'silovaya-trenirovka-dlya-muzhchin-nabiraem-massu-z',
    'womens_workout_1': 'trenirovka-dlya-devushek-stroynoe-telo-za-30-dney',
    'diet_1': 'sredizemnomorskaya-dieta-nauchno-dokazannyy-put-k-',
    'motivation_1': 'nachni-segodnya-pochemu-ne-stoit-otkladyvat-trenir'
}

def _transliterate_slug(текст: str) -> str:
    транслит = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    text = (текст or '').lower()
    slug = ''
    for char in text:
        if char in транслит:
            slug += транслит[char]
        elif char.isalnum() or char in '- ':
            slug += char
        else:
            slug += '-'
    slug = re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')[:50]
    return slug

def создать_slug(текст, post_id):
    """Создаёт URL-friendly slug с гарантией уникальности."""
    if post_id in SLUG_CACHE:
        return SLUG_CACHE[post_id]
    if post_id in KNOWN_SLUGS:
        slug = KNOWN_SLUGS[post_id]
    else:
        slug = _transliterate_slug(текст)
        if not slug:
            slug = post_id
    if slug in USED_SLUGS:
        suffix = re.sub(r'[^a-z0-9]', '', (post_id or '')[-8:].lower())
        if suffix:
            slug = f"{slug[:42]}-{suffix}"
        else:
            slug = f"{slug[:42]}-{abs(hash(post_id)) % 10000}"
    USED_SLUGS.add(slug)
    SLUG_CACHE[post_id] = slug
    return slug

def извлечь_заголовки_из_текста(текст):
    """Извлекает заголовки из текста и создаёт уникальную структуру H1-H6"""
    if not текст:
        return {'h1': '', 'h2': [], 'h3': [], 'h4': []}
    
    # Ищем заголовки в HTML
    h2_pattern = r'<h2[^>]*>(.*?)</h2>'
    h3_pattern = r'<h3[^>]*>(.*?)</h3>'
    h4_pattern = r'<h4[^>]*>(.*?)</h4>'
    
    h2_matches = re.findall(h2_pattern, текст, re.IGNORECASE | re.DOTALL)
    h3_matches = re.findall(h3_pattern, текст, re.IGNORECASE | re.DOTALL)
    h4_matches = re.findall(h4_pattern, текст, re.IGNORECASE | re.DOTALL)
    
    # Очищаем от HTML тегов
    def очистить(html):
        return re.sub(r'<[^>]+>', '', html).strip()
    
    return {
        'h1': '',  # H1 будет заголовком статьи
        'h2': [очистить(h) for h in h2_matches],
        'h3': [очистить(h) for h in h3_matches],
        'h4': [очистить(h) for h in h4_matches]
    }

def создать_уникальный_alt_для_изображения(заголовок, теги, индекс=0):
    """Создаёт уникальный alt и title для изображения (без ID и лишних слов)"""
    # Убираем эмодзи и лишние символы из заголовка для alt
    чистый_заголовок = re.sub(r'[🔥💪🧠⏰💥🚫]', '', заголовок).strip()
    
    вариации_alt = [
        f"{чистый_заголовок}",
        f"Иллюстрация: {чистый_заголовок}",
        f"Фото к статье о {', '.join(теги[:1]) if теги else 'фитнесе'}",
        f"Изображение для статьи: {чистый_заголовок}",
        f"Фотография: {чистый_заголовок}"
    ]
    
    вариации_title = [
        f"{чистый_заголовок}",
        f"Иллюстрация статьи: {чистый_заголовок}",
        f"Фото для материала о {', '.join(теги[:1]) if теги else 'фитнесе'}",
        f"Изображение статьи: {чистый_заголовок}",
        f"Фотография статьи: {чистый_заголовок}"
    ]
    
    alt = вариации_alt[индекс % len(вариации_alt)]
    title = вариации_title[индекс % len(вариации_title)]
    
    # НЕ добавляем ID - Google не любит спам в alt
    return alt, title

def создать_уникальную_ссылку_на_таймер(текст, теги, индекс=0):
    """Создаёт уникальную ссылку на таймер с уникальным title"""
    вариации_текста = [
        "Запусти таймер TABATA",
        "Используй таймер HIIT",
        "Начни тренировку с таймером",
        "Открой таймер для интервальных тренировок",
        "Запусти онлайн таймер",
        "Используй таймер AMRAP",
        "Начни с таймером EMOM",
        "Открой таймер TABATATIMER.RU"
    ]
    
    вариации_title = [
        f"Запустить таймер для тренировки: {', '.join(теги[:2])}",
        f"Онлайн таймер для интервальных тренировок - {', '.join(теги[:2])}",
        f"Таймер TABATA, HIIT, AMRAP, EMOM для {', '.join(теги[:2])}",
        f"Бесплатный онлайн таймер для тренировок: {', '.join(теги[:2])}",
        f"Таймер для фитнеса: {', '.join(теги[:2])}",
        f"Интервальный таймер онлайн: {', '.join(теги[:2])}",
        f"Таймер тренировок TABATATIMER.RU: {', '.join(теги[:2])}",
        f"Онлайн секундомер для {', '.join(теги[:2])}"
    ]
    
    текст_ссылки = вариации_текста[индекс % len(вариации_текста)]
    title_ссылки = вариации_title[индекс % len(вариации_title)]
    
    # Добавляем уникальный идентификатор
    уникальный_суффикс = f" | ID: {hash(текст + str(индекс)) % 10000}"
    title_ссылки += уникальный_суффикс
    
    return текст_ссылки, title_ссылки

def создать_галерею_изображений(изображения, заголовок, теги):
    """
    Создаёт галерею-слайдер с изображениями статьи, БЕЗ дублирования первого.
    
    - Первое изображение показывается только в шапке статьи (article.blog-post-header > img.blog-post-image).
    - В галерею попадают только изображения со 2-го и далее — чтобы первое не дублировалось в блоке галереи.
    - Если изображение одно, галерея не создаётся (вызов с len(изображения) > 1).
    """
    if not изображения:
        return ''  # Если нет изображений, галерея не нужна
    
    # Первое изображение уже в шапке статьи — в галерею не включаем, иначе дубль в DOM
    все_изображения_для_галереи = изображения[1:]
    
    if not все_изображения_для_галереи:
        return ''
    
    # Создаём уникальный ID для галереи
    gallery_id = f"gallery-{abs(hash(заголовок)) % 10000}"
    # Заголовок галереи — мотивационная фраза по контексту (девушкам / мужчинам / питание)
    фраза = выбрать_мотивационную_фразу(теги, заголовок)
    галерея_html = f'''
    <div class="blog-post-gallery">
        <h3>{фраза}</h3>
        <div class="blog-gallery-slider" id="{gallery_id}">
            <div class="blog-gallery-main">
                <img id="{gallery_id}-main" src="" alt="" class="blog-gallery-main-image">
                <button class="blog-gallery-prev" onclick="galleryPrev('{gallery_id}')">‹</button>
                <button class="blog-gallery-next" onclick="galleryNext('{gallery_id}')">›</button>
            </div>
            <div class="blog-gallery-thumbnails">
'''
    
    for idx, img_dict in enumerate(все_изображения_для_галереи):
        img_url = img_dict.get('url', '')
        if not img_url:
            continue
            
        img_alt = _без_упоминания_источника(img_dict.get('alt', '') or f"{заголовок} - фото {idx + 1}")
        img_title = _без_упоминания_источника(img_dict.get('title', '') or f"{заголовок} - изображение {idx + 1}")
        
        # Создаём уникальные alt и title для каждого изображения
        alt, title = создать_уникальный_alt_для_изображения(заголовок, теги, idx + 1)
        if img_alt and img_alt.strip():
            alt = img_alt
        if img_title and img_title.strip():
            title = img_title
        
        # Экранируем кавычки в alt и title
        alt = alt.replace('"', '&quot;')
        title = title.replace('"', '&quot;')
        
        # Первое изображение в слайдере показываем сразу
        active_class = 'active' if idx == 0 else ''
        
        галерея_html += f'''
                <div class="blog-gallery-thumb {active_class}" onclick="galleryShow('{gallery_id}', {idx})">
                    <img src="{img_url}" alt="{alt}" title="{title}" loading="lazy" class="blog-gallery-thumb-image">
                </div>
'''
    
    # Подготавливаем данные для JavaScript
    images_data = []
    for img_dict in все_изображения_для_галереи:
        img_url = img_dict.get('url', '')
        if img_url:
            img_alt = _без_упоминания_источника(img_dict.get('alt', '') or f"{заголовок} - фото")
            img_title = _без_упоминания_источника(img_dict.get('title', '') or f"{заголовок} - изображение")
            # Экранируем для JavaScript
            img_alt = img_alt.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
            img_title = img_title.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
            images_data.append({
                'url': img_url,
                'alt': img_alt,
                'title': img_title
            })
    
    images_json = json.dumps(images_data, ensure_ascii=False)
    
    галерея_html += f'''
            </div>
        </div>
    </div>
    
    <script>
        // Инициализация галереи
        (function() {{
            const galleryId = '{gallery_id}';
            const images = {images_json};
            
            // Сохраняем данные галереи в глобальный объект
            if (!window.blogGalleries) {{
                window.blogGalleries = {{}};
            }}
            window.blogGalleries[galleryId] = images;
            
            if (images.length > 0) {{
                // Показываем первое изображение
                galleryShow(galleryId, 0);
            }}
        }})();
        
        function galleryShow(galleryId, index) {{
            const gallery = document.getElementById(galleryId);
            if (!gallery || !window.blogGalleries || !window.blogGalleries[galleryId]) return;
            
            const images = window.blogGalleries[galleryId];
            
            if (index < 0 || index >= images.length) return;
            
            const mainImg = document.getElementById(galleryId + '-main');
            const thumbs = gallery.querySelectorAll('.blog-gallery-thumb');
            
            if (mainImg && images[index]) {{
                mainImg.src = images[index].url;
                mainImg.alt = images[index].alt || '';
                mainImg.title = images[index].title || '';
            }}
            
            // Обновляем активный класс
            thumbs.forEach((thumb, i) => {{
                if (i === index) {{
                    thumb.classList.add('active');
                }} else {{
                    thumb.classList.remove('active');
                }}
            }});
        }}
        
        function galleryNext(galleryId) {{
            const gallery = document.getElementById(galleryId);
            if (!gallery || !window.blogGalleries || !window.blogGalleries[galleryId]) return;
            const active = gallery.querySelector('.blog-gallery-thumb.active');
            if (!active) {{
                galleryShow(galleryId, 0);
                return;
            }}
            const thumbs = Array.from(gallery.querySelectorAll('.blog-gallery-thumb'));
            const currentIndex = thumbs.indexOf(active);
            const nextIndex = (currentIndex + 1) % thumbs.length;
            galleryShow(galleryId, nextIndex);
        }}
        
        function galleryPrev(galleryId) {{
            const gallery = document.getElementById(galleryId);
            if (!gallery || !window.blogGalleries || !window.blogGalleries[galleryId]) return;
            const active = gallery.querySelector('.blog-gallery-thumb.active');
            if (!active) {{
                const thumbs = gallery.querySelectorAll('.blog-gallery-thumb');
                galleryShow(galleryId, thumbs.length - 1);
                return;
            }}
            const thumbs = Array.from(gallery.querySelectorAll('.blog-gallery-thumb'));
            const currentIndex = thumbs.indexOf(active);
            const prevIndex = (currentIndex - 1 + thumbs.length) % thumbs.length;
            galleryShow(galleryId, prevIndex);
        }}
    </script>
'''
    return галерея_html

def создать_заключительный_блок_про_таймер(текст, теги):
    """Создаёт заключительный блок про применение интервального таймера"""
    # Определяем подходящий режим таймера на основе тегов и содержания
    режим_таймера = None
    описание_режима = ""
    
    текст_нижний = текст.lower()
    
    # Определяем режим по ключевым словам
    if 'tabata' in текст_нижний or 'табата' in текст_нижний:
        режим_таймера = 'TABATA'
        описание_режима = "Режим TABATA идеально подходит для высокоинтенсивных интервальных тренировок: 20 секунд работы и 10 секунд отдыха. Этот режим поможет вам максимально эффективно сжигать калории и улучшать выносливость."
    elif 'hiit' in текст_нижний or 'высокоинтенсивн' in текст_нижний or 'кардио' in текст_нижний:
        режим_таймера = 'HIIT'
        описание_режима = "Режим HIIT (высокоинтенсивная интервальная тренировка) отлично подходит для кардио-нагрузок и сжигания жира. Настройте интервалы работы и отдыха под свои возможности."
    elif 'emom' in текст_нижний or 'каждую минуту' in текст_нижний:
        режим_таймера = 'EMOM'
        описание_режима = "Режим EMOM (Every Minute On the Minute) идеален для силовых тренировок с фиксированным временем выполнения упражнений. Выполняйте заданное количество повторений в начале каждой минуты."
    elif 'amrap' in текст_нижний or 'максимум повторений' in текст_нижний:
        режим_таймера = 'AMRAP'
        описание_режима = "Режим AMRAP (As Many Rounds As Possible) подходит для круговых тренировок на максимальное количество раундов за заданное время. Отлично развивает выносливость и силу."
    else:
        # По умолчанию используем TABATA или HIIT в зависимости от тегов
        if 'Тренировка' in теги or 'Мужчинам' in теги or 'Девушкам' in теги:
            режим_таймера = 'TABATA'
            описание_режима = "Режим TABATA идеально подходит для интервальных тренировок: 20 секунд работы и 10 секунд отдыха. Этот режим поможет вам максимально эффективно сжигать калории и улучшать выносливость."
        else:
            режим_таймера = 'HIIT'
            описание_режима = "Режим HIIT (высокоинтенсивная интервальная тренировка) отлично подходит для эффективных тренировок. Настройте интервалы работы и отдыха под свои возможности."
    
    # Создаём уникальную ссылку
    текст_ссылки, title_ссылки = создать_уникальную_ссылку_на_таймер(текст, теги, 999)
    
    блок = f'''
    <div class="blog-timer-block">
        <h3>Как использовать интервальный таймер для этой программы</h3>
        <p>{описание_режима}</p>
        <p>Для этой программы тренировок используйте режим <strong>{режим_таймера}</strong> на <a href="https://www.tabatatimer.ru/#timer" target="_blank" rel="noopener noreferrer" title="{title_ссылки}">tabatatimer.ru</a>. Это поможет вам:</p>
        <ul>
            <li>Строго соблюдать интервалы работы и отдыха</li>
            <li>Максимально эффективно использовать время тренировки</li>
            <li>Отслеживать прогресс и улучшать результаты</li>
            <li>Поддерживать высокую интенсивность на протяжении всей тренировки</li>
        </ul>
        <p><a href="https://www.tabatatimer.ru/#timer" target="_blank" rel="noopener noreferrer" title="{title_ссылки}">{текст_ссылки}</a> прямо сейчас и начните тренироваться эффективнее!</p>
    </div>
    '''
    return блок

def добавить_пояснения_для_имён(текст):
    """Добавляет краткие пояснения в скобках для имён и персоналий"""
    if not текст:
        return текст
    
    # Словарь имён и их пояснений
    имена_пояснения = {
        r'\bБрэндон\b': 'Брэндон (американский фитнес-тренер)',
        r'\bBrandon\b': 'Brandon (американский фитнес-тренер)',
    }
    
    # Заменяем имена, но только если после них нет пояснения в скобках
    for паттерн, замена in имена_пояснения.items():
        # Проверяем, нет ли уже пояснения после имени (в скобках)
        паттерн_с_пояснением = паттерн.replace(r'\b', '') + r'\s*\([^)]+\)'
        if not re.search(паттерн_с_пояснением, текст, re.IGNORECASE):
            # Заменяем имя на имя с пояснением
            текст = re.sub(паттерн, замена, текст, flags=re.IGNORECASE)
    
    return текст

def форматировать_текст_для_html(текст, заголовок, теги):
    """
    Форматирует текст для HTML с чистой, читабельной структурой:
    - Убирает капс и звёздочки
    - Разбивает длинные абзацы на короткие (2-4 предложения)
    - Правильно оформляет списки упражнений
    - Использует семантическую структуру с <section>
    """
    if not текст:
        return ''
    
    # Добавляем пояснения для имён перед форматированием
    текст = добавить_пояснения_для_имён(текст)
    
    # Удаляем все ссылки на tabatatimer.ru из начала текста
    текст = re.sub(r'^.*?tabatatimer\.ru.*?\n', '', текст, flags=re.IGNORECASE | re.MULTILINE)
    текст = re.sub(r'^.*?Запусти таймер.*?\n', '', текст, flags=re.IGNORECASE | re.MULTILINE)
    
    # Убираем все эмодзи
    текст = re.sub(r'[🔥💪🧠⏰💥🚫✅❌⚠️📝📸🖼️🔍📥☁️]', '', текст)
    
    # Разбиваем текст на строки
    строки = текст.split('\n')
    блоки = []
    текущий_абзац = []
    текущий_список = []
    в_списке = False
    список_нумерованный = False
    
    # Список названий упражнений для распознавания
    названия_упражнений = [
        'приседания', 'выпады', 'прыжки', 'подъёмы', 'отжимания', 'скручивания', 
        'планка', 'бёрпи', 'альпинист', 'велосипед', 'мостик', 'махи', 'жим',
        'подтягивания', 'тяга', 'становая', 'бицепс', 'трицепс', 'плечи'
    ]
    
    def убрать_капс_и_форматировать(текст_строки):
        """Убирает капс, звёздочки, форматирует текст"""
        # Убираем markdown звёздочки
        текст_строки = re.sub(r'\*\*([^*]+)\*\*', r'\1', текст_строки)
        текст_строки = re.sub(r'\*([^*]+)\*', r'\1', текст_строки)
        
        # Проверяем, весь ли текст в капсе
        if текст_строки.isupper() and len(текст_строки) > 20:
            # Если длинный капс-абзац, разбиваем на предложения и делаем нормальный текст
            предложения = re.split(r'[.!?]\s+', текст_строки)
            нормализованные = []
            for предл in предложения:
                предл = предл.strip()
                if предл:
                    # Первую букву делаем заглавной, остальные - строчными
                    предл = предл[0].upper() + предл[1:].lower() if len(предл) > 1 else предл.upper()
                    нормализованные.append(предл)
            return '. '.join(нормализованные) + '.'
        elif текст_строки.isupper() and len(текст_строки) <= 20:
            # Короткий капс - делаем <strong> с нормальным регистром
            нормализованный = текст_строки[0].upper() + текст_строки[1:].lower() if len(текст_строки) > 1 else текст_строки
            return f'<strong>{нормализованный}</strong>'
        
        # Если есть части в капсе внутри текста, заменяем на <strong>
        def заменить_капс_части(match):
            капс_текст = match.group(0)
            if len(капс_текст) > 30:
                # Длинный капс - нормализуем
                нормализованный = капс_текст[0].upper() + капс_текст[1:].lower() if len(капс_текст) > 1 else капс_текст
                return нормализованный
            else:
                # Короткий капс - делаем <strong>
                нормализованный = капс_текст[0].upper() + капс_текст[1:].lower() if len(капс_текст) > 1 else капс_текст
                return f'<strong>{нормализованный}</strong>'
        
        # Находим слова/фразы в капсе (2+ заглавных букв подряд)
        текст_строки = re.sub(r'\b[A-ZА-ЯЁ]{2,}[A-ZА-ЯЁ\s]{0,30}\b', заменить_капс_части, текст_строки)
        
        return текст_строки
    
    def разбить_длинный_абзац(абзац_текст):
        """Разбивает длинный абзац на короткие (2-4 предложения)"""
        # Разбиваем по предложениям
        предложения = re.split(r'([.!?]\s+)', абзац_текст)
        # Объединяем разделители с предложениями
        объединённые = []
        for i in range(0, len(предложения), 2):
            if i < len(предложения):
                предложение = предложения[i]
                if i + 1 < len(предложения):
                    предложение += предложения[i + 1]
                if предложение.strip():
                    объединённые.append(предложение.strip())
        
        # Группируем по 2-4 предложения
        короткие_абзацы = []
        текущая_группа = []
        for предл in объединённые:
            текущая_группа.append(предл)
            # Если накопили 2-4 предложения или предложение очень длинное
            if len(текущая_группа) >= 3 or (len(текущая_группа) >= 2 and len(' '.join(текущая_группа)) > 300):
                короткие_абзацы.append(' '.join(текущая_группа))
                текущая_группа = []
        
        if текущая_группа:
            короткие_абзацы.append(' '.join(текущая_группа))
        
        return короткие_абзацы if короткие_абзацы else [абзац_текст]
    
    def это_упражнение_или_пункт(строка):
        """Проверяет, является ли строка упражнением или пунктом списка"""
        нижний = строка.lower().strip()
        # Нумерованный список
        if re.match(r'^\d+[\.\)]\s+', нижний):
            return True
        # Маркированный список
        if re.match(r'^[\*\-]\s+', нижний):
            return True
        # Содержит название упражнения
        if any(название in нижний for название in названия_упражнений):
            return True
        # Короткая строка (вероятно, пункт списка)
        if len(нижний) < 100 and (',' in нижний or ':' in нижний):
            return True
        return False
    
    for строка in строки:
        строка = строка.strip()
        
        # Пустая строка
        if not строка:
            if текущий_абзац:
                абзац_текст = ' '.join(текущий_абзац)
                # Разбиваем длинные абзацы
                короткие = разбить_длинный_абзац(абзац_текст)
                for короткий in короткие:
                    блоки.append({'type': 'paragraph', 'content': короткий})
                текущий_абзац = []
            if текущий_список:
                блоки.append({'type': 'list', 'content': текущий_список, 'ordered': список_нумерованный})
                текущий_список = []
                в_списке = False
                список_нумерованный = False
            continue
        
        # Markdown заголовки: ##, ###
        if строка.startswith('##'):
            if текущий_абзац:
                абзац_текст = ' '.join(текущий_абзац)
                короткие = разбить_длинный_абзац(абзац_текст)
                for короткий in короткие:
                    блоки.append({'type': 'paragraph', 'content': короткий})
                текущий_абзац = []
            if текущий_список:
                блоки.append({'type': 'list', 'content': текущий_список, 'ordered': список_нумерованный})
                текущий_список = []
                в_списке = False
                список_нумерованный = False
            
            текст_заголовка = re.sub(r'^#+\s*', '', строка).strip()
            текст_заголовка = убрать_капс_и_форматировать(текст_заголовка)
            # Убираем HTML теги из заголовка (оставляем только текст)
            текст_заголовка = re.sub(r'<[^>]+>', '', текст_заголовка)
            
            if строка.startswith('###'):
                блоки.append({'type': 'h3', 'content': текст_заголовка})
            else:
                блоки.append({'type': 'h2', 'content': текст_заголовка})
            continue
        
        # Горизонтальная линия: ---
        if строка.startswith('---') or строка == '---':
            if текущий_абзац:
                блоки.append({'type': 'paragraph', 'content': ' '.join(текущий_абзац)})
                текущий_абзац = []
            if текущий_список:
                блоки.append({'type': 'list', 'content': текущий_список, 'ordered': список_нумерованный})
                текущий_список = []
                в_списке = False
                список_нумерованный = False
            блоки.append({'type': 'hr', 'content': ''})
            continue
        
        # Нумерованный список: 1. пункт или 1) пункт
        if re.match(r'^\d+[\.\)]\s+', строка):
            if текущий_абзац:
                абзац_текст = ' '.join(текущий_абзац)
                короткие = разбить_длинный_абзац(абзац_текст)
                for короткий in короткие:
                    блоки.append({'type': 'paragraph', 'content': короткий})
                текущий_абзац = []
            if в_списке and текущий_список and not список_нумерованный:
                блоки.append({'type': 'list', 'content': текущий_список, 'ordered': False})
                текущий_список = []
            в_списке = True
            список_нумерованный = True
            пункт = re.sub(r'^\d+[\.\)]\s+', '', строка)
            пункт = убрать_капс_и_форматировать(пункт)
            # Обрабатываем markdown ссылки
            пункт = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', пункт)
            текущий_список.append(пункт)
            continue
        
        # Маркированный список: * пункт или - пункт
        if re.match(r'^[\*\-]\s+', строка):
            if текущий_абзац:
                абзац_текст = ' '.join(текущий_абзац)
                короткие = разбить_длинный_абзац(абзац_текст)
                for короткий in короткие:
                    блоки.append({'type': 'paragraph', 'content': короткий})
                текущий_абзац = []
            if в_списке and текущий_список and список_нумерованный:
                блоки.append({'type': 'list', 'content': текущий_список, 'ordered': True})
                текущий_список = []
            в_списке = True
            список_нумерованный = False
            пункт = re.sub(r'^[\*\-]\s+', '', строка)
            пункт = убрать_капс_и_форматировать(пункт)
            # Обрабатываем markdown ссылки
            пункт = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', пункт)
            текущий_список.append(пункт)
            continue
        
        # Заголовок h3 или h4 (старый формат с **)
        if строка.startswith('**') and строка.endswith('**') and len(строка) > 4:
            if текущий_абзац:
                блоки.append({'type': 'paragraph', 'content': ' '.join(текущий_абзац)})
                текущий_абзац = []
            if текущий_список:
                блоки.append({'type': 'list', 'content': текущий_список, 'ordered': список_нумерованный})
                текущий_список = []
                в_списке = False
                список_нумерованный = False
            
            текст_заголовка = строка.replace('**', '')
            if re.match(r'^День\s+\d+:', текст_заголовка, re.IGNORECASE):
                блоки.append({'type': 'h4', 'content': текст_заголовка})
            else:
                блоки.append({'type': 'h3', 'content': текст_заголовка})
            continue
        
        # Строка упражнения (список)
        if это_упражнение_или_пункт(строка):
            if текущий_абзац:
                блоки.append({'type': 'paragraph', 'content': ' '.join(текущий_абзац)})
                текущий_абзац = []
            в_списке = True
            # Форматируем строку упражнения
            пункт = убрать_капс_и_форматировать(строка)
            # Обрабатываем markdown ссылки
            пункт = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', пункт)
            текущий_список.append(пункт)
            continue
        
        # Обычный текст - закрываем список если был
        if в_списке:
            блоки.append({'type': 'list', 'content': текущий_список, 'ordered': список_нумерованный})
            текущий_список = []
            в_списке = False
            список_нумерованный = False
        
        # Обрабатываем markdown ссылки
        строка = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', строка)
        
        # Убираем капс и форматируем
        строка = убрать_капс_и_форматировать(строка)
        
        # Экранируем HTML, но сохраняем уже добавленные теги
        части = re.split(r'(<[^>]+>)', строка)
        экранированные_части = []
        for часть in части:
            if часть.startswith('<') and часть.endswith('>'):
                экранированные_части.append(часть)
            else:
                экранированные_части.append(html.escape(часть))
        строка = ''.join(экранированные_части)
        
        текущий_абзац.append(строка)
    
    # Закрываем последние блоки
    if текущий_абзац:
        абзац_текст = ' '.join(текущий_абзац)
        короткие = разбить_длинный_абзац(абзац_текст)
        for короткий in короткие:
            блоки.append({'type': 'paragraph', 'content': короткий})
    if текущий_список:
        блоки.append({'type': 'list', 'content': текущий_список, 'ordered': список_нумерованный})
    
    # Формируем HTML с семантической структурой
    результат = []
    в_секции = False
    
    for i, блок in enumerate(блоки):
        # Начинаем новую секцию при h2
        if блок['type'] == 'h2':
            if в_секции:
                результат.append('</section>')
            результат.append('<section>')
            в_секции = True
            результат.append(f"<h2>{html.escape(блок['content'])}</h2>")
        elif блок['type'] == 'h3':
            результат.append(f"<h3>{html.escape(блок['content'])}</h3>")
        elif блок['type'] == 'lead':
            результат.append(f'<p class="lead">{html.escape(блок["content"])}</p>')
        elif блок['type'] == 'list':
            элементы = ''.join([f"<li>{элемент}</li>" for элемент in блок['content']])
            тег_списка = '<ol>' if блок.get('ordered', False) else '<ul>'
            закрывающий_тег = '</ol>' if блок.get('ordered', False) else '</ul>'
            результат.append(f"{тег_списка}{элементы}{закрывающий_тег}")
        elif блок['type'] == 'paragraph':
            # Контент уже может содержать HTML теги
            результат.append(f"<p>{блок['content']}</p>")
    
    # Закрываем последнюю секцию
    if в_секции:
        результат.append('</section>')
    
    текст_html = ''.join(результат)
    
    # Добавляем заключительный блок про таймер в конец
    заключительный_блок = создать_заключительный_блок_про_таймер(текст, теги)
    текст_html += заключительный_блок
    
    # Обрабатываем изображения - добавляем уникальные alt и title
    счётчик_изображений = 0
    def заменить_изображение(match):
        nonlocal счётчик_изображений
        полный_тег = match.group(0)
        alt, title = создать_уникальный_alt_для_изображения(заголовок, теги, счётчик_изображений)
        счётчик_изображений += 1
        
        if 'alt=' in полный_тег:
            полный_тег = re.sub(r'alt=["\'][^"\']*["\']', f'alt="{alt}"', полный_тег)
        else:
            полный_тег = полный_тег.replace('<img', f'<img alt="{alt}"')
        
        if 'title=' in полный_тег:
            полный_тег = re.sub(r'title=["\'][^"\']*["\']', f'title="{title}"', полный_тег)
        else:
            полный_тег = полный_тег.replace('<img', f'<img title="{title}"')
        
        return полный_тег
    
    текст_html = re.sub(r'<img[^>]*>', заменить_изображение, текст_html, flags=re.IGNORECASE)
    
    return текст_html

def адаптировать_заголовок_для_русской_аудитории(заголовок, текст=''):
    """
    ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Проверяет язык заголовка и переводит на русский если нужно
    
    Если заголовок на английском, создаёт русский заголовок на основе контента.
    """
    if not заголовок:
        return 'Статья о фитнесе'
    
    # Убираем только технические признаки источников (podcast #, episode, и т.д.)
    заголовок = re.sub(r'podcast\s*#?\s*\d+[,:]?\s*', '', заголовок, flags=re.IGNORECASE)
    заголовок = re.sub(r'episode\s*#?\s*\d+[,:]?\s*', '', заголовок, flags=re.IGNORECASE)
    заголовок = re.sub(r'#\s*\d+[,:]?\s*', '', заголовок)  # Убираем #123:
    заголовок = заголовок.strip(' -—:')
    
    # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Проверяем, является ли заголовок английским
    # Простая проверка: если больше 50% символов - латиница, считаем английским
    латиница = sum(1 for c in заголовок if c.isalpha() and ord(c) < 128 and c.isascii())
    кириллица = sum(1 for c in заголовок if c.isalpha() and ord(c) >= 1040 and ord(c) <= 1103)
    всего_букв = латиница + кириллица
    
    if всего_букв > 0 and латиница > кириллица:
        # Заголовок на английском - создаём русский на основе контента
        try:
            from create_title_from_content import создать_заголовок_на_основе_контента
            заголовок_русский = создать_заголовок_на_основе_контента(текст, заголовок)
            if заголовок_русский and заголовок_русский != заголовок:
                print(f"✅ Заголовок переведён на русский: '{заголовок}' → '{заголовок_русский}'")
                return заголовок_русский
        except Exception as e:
            print(f"⚠️ Не удалось перевести заголовок на русский: {e}")
    
    return заголовок

def сгенерировать_html_страницу(пост):
    """Генерирует HTML страницу для поста"""
    post_id = пост.get('id', 'unknown')
    заголовок_оригинальный = пост.get('title', 'Статья')
    текст = пост.get('text', '')
    
    # ✅ ИСПРАВЛЕНИЕ: Используем оригинальный заголовок из спарсенной статьи
    # Удалена логика адаптации с жестко закодированными заголовками
    заголовок = адаптировать_заголовок_для_русской_аудитории(заголовок_оригинальный, текст)
    
    изображение_url = пост.get('image', 'https://www.tabatatimer.ru/images/og-image.jpg')
    все_изображения_поста = пост.get('images', [])  # Список всех релевантных изображений
    теги = пост.get('tags', [])
    дата_публикации = пост.get('date', datetime.now().isoformat())
    timestamp = пост.get('timestamp', int(datetime.now().timestamp()))
    
    # Используем все изображения из поста, если они есть
    обработанные_изображения = []
    if все_изображения_поста:
        обработанные_изображения = все_изображения_поста
    elif изображение_url:
        # Если нет массива images, создаём из главного изображения
        обработанные_изображения = [{
            'url': изображение_url,
            'alt': f"{заголовок} - фото тренировки и фитнеса",
            'title': f"{заголовок} - профессиональное фото тренировки",
            'is_main': True
        }]
    
    # Главное изображение для Open Graph и Schema.org (первое или помеченное как главное)
    # Для постов о питании/рецептах: не сток Fitness | Woman, не служебный кадр — фото блюда из галереи
    источник = (пост.get('source') or '').lower()
    теги_lower = [str(t).strip().lower() for t in (теги or [])]
    # Только реальные рецепты из пайплайна рецептов или явный тег «рецепт».
    # Не используем «питание»/«диеты» — иначе статьи WH про режим питания при тренировках
    # ошибочно получают логику «фото блюда» при том, что hero — сток Fitness | Woman.
    пост_про_еду = (
        источник in ('recipes', 'skinnyms_recipes')
        or any(t in теги_lower for t in ('рецепт', 'рецепты'))
    )
    главное_изображение = None
    if пост_про_еду and обработанные_изображения:
        главное_изображение = выбрать_главное_изображение_для_рецепта(обработанные_изображения)
    if not главное_изображение:
        for img_dict in обработанные_изображения:
            if img_dict.get('is_main', False):
                главное_изображение = img_dict
                break
    if not главное_изображение and обработанные_изображения:
        главное_изображение = обработанные_изображения[0]

    # Синхронизируем порядок images[] и post.image с выбранным hero (превью + модалка на blog.html)
    if пост_про_еду and все_изображения_поста and главное_изображение:
        imgs = пост.get('images')
        if imgs and isinstance(imgs, list) and len(imgs) > 0:

            def _norm_u(u):
                return (u or '').split('?')[0].rstrip('/').lower()

            gurl = _norm_u(главное_изображение.get('url'))
            ix = next((i for i, x in enumerate(imgs) if _norm_u(x.get('url')) == gurl), None)
            if ix is not None and ix > 0:
                row = imgs.pop(ix)
                imgs.insert(0, row)
                пост['_blog_json_dirty'] = True
            for i, im in enumerate(imgs):
                im['is_main'] = (i == 0)
            first_u = imgs[0].get('url')
            if first_u and _norm_u(пост.get('image')) != _norm_u(first_u):
                пост['image'] = first_u
                пост['_blog_json_dirty'] = True

    изображение = главное_изображение['url'] if главное_изображение else изображение_url
    
    # Создаём slug для URL
    # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Если в посте уже есть URL, извлекаем slug из него
    # Это гарантирует, что slug совпадает с тем, что был сохранен в blog-posts.json
    существующий_url = пост.get('url', '')
    if существующий_url and '/blog/' in существующий_url:
        # Извлекаем slug из URL (например: /blog/trenirovka-tabata-sekretnyy-klyuch-k-rezultatu.html)
        # Или: https://www.tabatatimer.ru/blog/30-minute-leg-workout-circuit-for-goddess-worthy-l.html
        slug = существующий_url.split('/blog/')[-1].replace('.html', '').strip()
        if not slug:
            # Если slug пустой, генерируем из заголовка
            slug = создать_slug(заголовок, post_id)
    else:
        # Генерируем slug из заголовка
        slug = создать_slug(заголовок, post_id)
    
    url = f"https://www.tabatatimer.ru/blog/{slug}.html"
    
    # Создаём чистое описание для meta description (без Markdown, без ID, без мусора)
    описание_текст = очистить_текст_от_html(текст)
    if описание_текст:
        # Разбиваем на строки для правильной обработки Markdown
        строки = описание_текст.split('\n')
        очищенные_строки = []
        for строка in строки:
            строка = строка.strip()
            if not строка:
                continue
            # Убираем Markdown символы из начала строки
            строка = re.sub(r'^#+\s*', '', строка)
            строка = re.sub(r'^\*+\s*', '', строка)
            строка = re.sub(r'^---+\s*', '', строка)
            строка = re.sub(r'^\d+\.\s*', '', строка)  # Убираем нумерацию
            # Убираем Markdown форматирование
            строка = re.sub(r'\*\*([^*]+)\*\*', r'\1', строка)  # Убираем **
            строка = re.sub(r'\*([^*]+)\*', r'\1', строка)  # Убираем *
            if строка:
                очищенные_строки.append(строка)
        
        # Собираем обратно в текст
        описание_текст = ' '.join(очищенные_строки)
        
        # Берём первые 2-3 предложения (до 155 символов для Google)
        предложения = re.split(r'[.!?]\s+', описание_текст)
        описание = ''
        for предложение in предложения:
            if len(описание + предложение) <= 155:
                описание += предложение + '. '
            else:
                break
        
        описание = описание.strip()
        if not описание or len(описание) < 50:
            # Если не получилось, берём первые 155 символов
            описание = описание_текст[:155].strip()
            if len(описание_текст) > 155:
                описание = описание.rsplit(' ', 1)[0] + '...'  # Обрезаем по последнему слову
    else:
        описание = f"Полезная статья о фитнесе и тренировках. {', '.join(теги)}."
    
    # Создаём уникальный Title
    уникальный_title = f"{заголовок} | Блог TABATATIMER.RU | {', '.join(теги)}"
    
    # Форматируем дату
    try:
        дата_объект = datetime.fromisoformat(дата_публикации.replace('Z', '+00:00'))
        дата_публикации_iso = дата_объект.strftime('%Y-%m-%d')
        дата_публикации_ru = дата_объект.strftime('%d.%m.%Y')
    except:
        дата_публикации_iso = datetime.now().strftime('%Y-%m-%d')
        дата_публикации_ru = datetime.now().strftime('%d.%m.%Y')
    
    # Извлекаем заголовки для структуры
    заголовки = извлечь_заголовки_из_текста(текст)
    
    # Форматируем текст для HTML с уникальными ссылками и изображениями
    текст_html = форматировать_текст_для_html(текст, заголовок, теги)
    
    # Создаём уникальные alt и title для главного изображения
    alt_изображения, title_изображения = создать_уникальный_alt_для_изображения(заголовок, теги, 0)
    
    # Ключевые слова из тегов
    ключевые_слова = ', '.join(теги) + ', фитнес, тренировки, табата, hiit, amrap, emom'
    
    # Экранируем фигурные скобки для JavaScript
    js_redirect = """if (window.location.hostname === 'tabatatimer.ru') {
            window.location.replace('https://www.tabatatimer.ru' + window.location.pathname + window.location.search + window.location.hash);
        }"""
    
    js_metrika = """(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
       m[i].l=1*new Date();
       for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
       k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
       (window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");

       ym(42580049, "init", {
            clickmap:true,
            trackLinks:true,
            accurateTrackBounce:true,
            webvisor:true,
            trackHash:true
       });"""
    
    html = f"""<!DOCTYPE HTML>
<html lang="ru" prefix="article: http://ogp.me/ns/article#">
<head>
    <meta charset="utf-8" />
    
    <!-- Автоматический редирект с tabatatimer.ru на www.tabatatimer.ru -->
    <script>
        {js_redirect}
    </script>
    
    <!-- Yandex.Metrika counter -->
    <script type="text/javascript">
       {js_metrika}
    </script>
    <noscript><div><img src="https://mc.yandex.ru/watch/42580049" style="position:absolute; left:-9999px;" alt="" /></div></noscript>
    <!-- /Yandex.Metrika counter -->
    
    <title>{уникальный_title}</title>
    
    <meta name="description" content="{описание}">
    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no" />
    <meta name="author" content="TABATATIMER.RU">
    <meta name="robots" content="index, follow">
    <meta http-equiv="X-Robots-Tag" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
    <link rel="canonical" href="{url}">
    <link rel="alternate" hreflang="ru" href="{url}">
    <link rel="alternate" hreflang="x-default" href="{url}">
    <meta name="yandex-verification" content="5e156b77592f12f7" />
    
    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="{url}">
    <meta property="og:title" content="{заголовок}">
    <meta property="og:description" content="{описание}">
    <meta property="og:image" content="{изображение}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:image:type" content="image/jpeg">
    <meta property="og:image:alt" content="{заголовок}">
    <meta property="og:locale" content="ru_RU">
    <meta property="og:site_name" content="TABATATIMER.RU">
    <meta property="article:published_time" content="{дата_публикации_iso}">
    <meta property="article:modified_time" content="{дата_публикации_iso}">
    <meta property="article:author" content="TABATATIMER.RU">
    <meta property="article:section" content="Фитнес">
    {''.join([f'<meta property="article:tag" content="{тег}">' for тег in теги])}
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="{url}">
    <meta name="twitter:title" content="{заголовок}">
    <meta name="twitter:description" content="{описание}">
    <meta name="twitter:image" content="{изображение}">
    
    <!-- Schema.org JSON-LD -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": {json.dumps(заголовок)},
        "description": {json.dumps(описание)},
        "image": {json.dumps(изображение)},
        "datePublished": "{дата_публикации_iso}",
        "dateModified": "{дата_публикации_iso}",
        "author": {{
            "@type": "Organization",
            "name": "TABATATIMER.RU",
            "url": "https://www.tabatatimer.ru/"
        }},
        "publisher": {{
            "@type": "Organization",
            "name": "TABATATIMER.RU",
            "url": "https://www.tabatatimer.ru/",
            "logo": {{
                "@type": "ImageObject",
                "url": "https://www.tabatatimer.ru/images/og-image.jpg"
            }}
        }},
        "mainEntityOfPage": {{
            "@type": "WebPage",
            "@id": {json.dumps(url)}
        }},
        "keywords": {json.dumps(ключевые_слова)}
    }}
    </script>
    
    <!-- Breadcrumb Schema -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{
                "@type": "ListItem",
                "position": 1,
                "name": "Главная",
                "item": "https://www.tabatatimer.ru/"
            }},
            {{
                "@type": "ListItem",
                "position": 2,
                "name": "Блог",
                "item": "https://www.tabatatimer.ru/blog.html"
            }},
            {{
                "@type": "ListItem",
                "position": 3,
                "name": {json.dumps(заголовок)},
                "item": {json.dumps(url)}
            }}
        ]
    }}
    </script>
    
    <!-- Favicon -->
    <link rel="icon" type="image/png" href="../favicon.ico">
    
    <!-- CSS -->
    <link rel="stylesheet" href="../assets/css/main.css">
    <link rel="stylesheet" href="../assets/css/burger-menu.css">
    <link rel="stylesheet" href="../assets/css/font-awesome.min.css">
    
    <style>
        html, body {{
            overflow-x: hidden;
            margin: 0;
            padding: 0;
        }}
        
        .blog-post-page {{
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            color: rgba(255, 255, 255, 0.9);
            background: #1a1a1a;
            min-height: 100vh;
        }}
        
        .blog-post-header {{
            margin-bottom: 40px;
        }}
        
        .blog-post-title {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 20px;
            color: #fff;
            line-height: 1.2;
        }}
        
        .blog-post-meta {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 30px;
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.9rem;
        }}
        
        .blog-post-image {{
            width: 100%;
            max-height: 500px;
            object-fit: cover;
            border-radius: 12px;
            margin-bottom: 30px;
        }}
        
        .blog-post-gallery {{
            margin: 40px 0;
            padding: 30px 0;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .blog-post-gallery h3 {{
            font-size: 1.5rem;
            margin: 0 0 20px 0;
            color: #7af5ff;
        }}
        
        .blog-gallery-slider {{
            position: relative;
        }}
        
        .blog-gallery-main {{
            position: relative;
            margin-bottom: 20px;
            border-radius: 12px;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.05);
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .blog-gallery-main-image {{
            width: 100%;
            height: auto;
            max-height: 600px;
            object-fit: contain;
            display: block;
        }}
        
        .blog-gallery-prev,
        .blog-gallery-next {{
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(122, 245, 255, 0.8);
            border: none;
            color: #1a1a1a;
            font-size: 2rem;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
        }}
        
        .blog-gallery-prev {{
            left: 15px;
        }}
        
        .blog-gallery-next {{
            right: 15px;
        }}
        
        .blog-gallery-prev:hover,
        .blog-gallery-next:hover {{
            background: #7af5ff;
            transform: translateY(-50%) scale(1.1);
        }}
        
        .blog-gallery-thumbnails {{
            display: flex;
            gap: 10px;
            overflow-x: auto;
            padding: 10px 0;
            scrollbar-width: thin;
            scrollbar-color: rgba(122, 245, 255, 0.3) transparent;
        }}
        
        .blog-gallery-thumbnails::-webkit-scrollbar {{
            height: 8px;
        }}
        
        .blog-gallery-thumbnails::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
        }}
        
        .blog-gallery-thumbnails::-webkit-scrollbar-thumb {{
            background: rgba(122, 245, 255, 0.3);
            border-radius: 4px;
        }}
        
        .blog-gallery-thumbnails::-webkit-scrollbar-thumb:hover {{
            background: rgba(122, 245, 255, 0.5);
        }}
        
        .blog-gallery-thumb {{
            flex-shrink: 0;
            width: 120px;
            height: 120px;
            border-radius: 8px;
            overflow: hidden;
            cursor: pointer;
            border: 2px solid transparent;
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .blog-gallery-thumb:hover {{
            border-color: rgba(122, 245, 255, 0.5);
            transform: scale(1.05);
        }}
        
        .blog-gallery-thumb.active {{
            border-color: #7af5ff;
            box-shadow: 0 0 15px rgba(122, 245, 255, 0.5);
        }}
        
        .blog-gallery-thumb-image {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}
        
        @media (max-width: 768px) {{
            .blog-gallery-main {{
                min-height: 300px;
            }}
            
            .blog-gallery-main-image {{
                max-height: 400px;
            }}
            
            .blog-gallery-thumb {{
                width: 80px;
                height: 80px;
            }}
            
            .blog-gallery-prev,
            .blog-gallery-next {{
                width: 40px;
                height: 40px;
                font-size: 1.5rem;
            }}
        }}
        
        .blog-post-content {{
            line-height: 1.8;
            font-size: 1.1rem;
        }}
        
        .blog-post-content section {{
            margin: 40px 0;
            padding: 0;
        }}
        
        .blog-post-content section:first-of-type {{
            margin-top: 0;
        }}
        
        .blog-post-content section:last-of-type {{
            margin-bottom: 0;
        }}
        
        .blog-post-content h2 {{
            font-size: 1.8rem;
            margin: 30px 0 20px 0;
            color: #7af5ff;
            font-weight: 600;
            line-height: 1.3;
        }}
        
        .blog-post-content section > h2:first-child {{
            margin-top: 0;
        }}
        
        .blog-post-content h3 {{
            font-size: 1.5rem;
            margin: 30px 0 12px 0;
            color: rgba(255, 255, 255, 0.9);
        }}
        
        .blog-post-content h3:first-of-type {{
            margin-top: 40px;
        }}
        
        .blog-post-content h4 {{
            font-size: 1.2rem;
            margin: 20px 0 10px 0;
            color: rgba(255, 255, 255, 0.85);
        }}
        
        .blog-post-content p {{
            margin: 0 0 15px 0;
        }}
        
        .blog-post-content p.lead {{
            font-size: 1.3rem;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.95);
            margin: 20px 0 25px 0;
            line-height: 1.6;
        }}
        
        .blog-post-content hr {{
            border: none;
            border-top: 1px solid rgba(255, 255, 255, 0.2);
            margin: 30px 0;
        }}
        
        .blog-post-content ul,
        .blog-post-content ol {{
            margin: 20px 0 25px 0;
            padding-left: 30px;
            line-height: 1.7;
        }}
        
        .blog-post-content li {{
            margin: 10px 0;
            line-height: 1.7;
            padding-left: 5px;
        }}
        
        .blog-post-content ul li {{
            list-style-type: disc;
        }}
        
        .blog-post-content ol li {{
            list-style-type: decimal;
        }}
        
        .blog-post-content a {{
            color: #7af5ff;
            text-decoration: none;
        }}
        
        .blog-post-content a:hover {{
            text-decoration: underline;
        }}
        
        .blog-post-tags {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .blog-post-tag {{
            padding: 5px 12px;
            background: rgba(122, 245, 255, 0.1);
            border: 1px solid rgba(122, 245, 255, 0.3);
            border-radius: 20px;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
            color: rgba(255, 255, 255, 0.8);
        }}
        
        .blog-post-tag:hover {{
            background: rgba(122, 245, 255, 0.2);
            border-color: #7af5ff;
            color: #7af5ff;
            transform: translateY(-2px);
        }}
        
        .blog-timer-block {{
            margin-top: 40px;
            padding: 30px;
            background: rgba(122, 245, 255, 0.05);
            border: 1px solid rgba(122, 245, 255, 0.2);
            border-radius: 12px;
        }}
        
        .blog-timer-block h3 {{
            color: #7af5ff;
            margin-top: 0;
            margin-bottom: 20px;
            font-size: 1.3rem;
        }}
        
        .blog-timer-block ul {{
            margin: 15px 0;
            padding-left: 25px;
        }}
        
        .blog-timer-block li {{
            margin: 8px 0;
            color: rgba(255, 255, 255, 0.8);
        }}
        
        .blog-timer-block a {{
            color: #7af5ff;
            text-decoration: none;
        }}
        
        .blog-timer-block a:hover {{
            text-decoration: underline;
        }}
        
        .blog-post-back {{
            display: inline-block;
            margin-bottom: 30px;
            color: #7af5ff;
            text-decoration: none;
            font-size: 0.9rem;
        }}
        
        .blog-post-back:hover {{
            text-decoration: underline;
        }}
        
        /* Блок подписки на Telegram канал */
        .blog-subscribe-footer {{
            margin-top: 60px;
            padding: 40px 20px;
            background: linear-gradient(135deg, rgba(122, 245, 255, 0.08) 0%, rgba(122, 245, 255, 0.03) 100%);
            border-top: 1px solid rgba(122, 245, 255, 0.15);
        }}
        
        .blog-subscribe-container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .blog-subscribe-content {{
            text-align: center;
        }}
        
        .blog-subscribe-title {{
            font-size: 1.5rem;
            color: #7af5ff;
            margin: 0 0 15px 0;
            font-weight: 600;
        }}
        
        .blog-subscribe-description {{
            color: rgba(255, 255, 255, 0.85);
            font-size: 1rem;
            line-height: 1.6;
            margin: 0 0 25px 0;
        }}
        
        .blog-subscribe-description strong {{
            color: #7af5ff;
        }}
        
        .blog-subscribe-buttons {{
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        
        .blog-subscribe-button {{
            display: inline-block;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.95rem;
            transition: all 0.3s ease;
            border: 2px solid transparent;
            text-align: center;
        }}
        
        .blog-subscribe-button-primary {{
            padding: 12px 17px;
            background: #7af5ff;
            color: #1a1a2e;
            border-color: #7af5ff;
        }}
        
        .blog-subscribe-button-primary:hover {{
            background: #5dd5e5;
            border-color: #5dd5e5;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(122, 245, 255, 0.3);
        }}
        
        .blog-subscribe-button-secondary {{
            padding: 12px 17px;
            background: transparent;
            color: #7af5ff;
            border-color: #7af5ff;
        }}
        
        .blog-subscribe-button-secondary:hover {{
            background: rgba(122, 245, 255, 0.1);
            transform: translateY(-2px);
        }}
        
        @media (max-width: 768px) {{
            .blog-post-title {{
                font-size: 1.8rem;
            }}
            
            .blog-post-page {{
                padding: 20px 15px;
            }}
            
            .blog-subscribe-footer {{
                padding: 30px 15px;
                margin-top: 40px;
            }}
            
            .blog-subscribe-title {{
                font-size: 1.3rem;
            }}
            
            .blog-subscribe-buttons {{
                flex-wrap: wrap;
                gap: 15px;
            }}
            
            .blog-subscribe-button {{
                min-width: auto;
                flex: 1 1 auto;
                text-align: center;
                padding-left: 17px;
            }}
        }}
    </style>
</head>
<body>
    <div class="blog-post-page">
        <a href="../blog.html" class="blog-post-back">← Вернуться к блогу</a>
        
        <article class="blog-post-header">
            <h1 class="blog-post-title">{заголовок}</h1>
            
            <div class="blog-post-meta">
                <span>📅 {дата_публикации_ru}</span>
                <span>🏷️ {', '.join(теги)}</span>
            </div>
            
            {f'<img src="{изображение}" alt="{alt_изображения}" title="{title_изображения}" class="blog-post-image" loading="lazy">' if изображение else ''}
        </article>
        
        <div class="blog-post-content">
            {текст_html}
            
            <!-- Галерея всех релевантных изображений из статьи -->
            {создать_галерею_изображений(обработанные_изображения, заголовок, теги) if обработанные_изображения and len(обработанные_изображения) > 1 else ''}
        </div>
        
        <div class="blog-post-tags">
            {''.join([f'<a href="../blog.html?filter={quote(тег)}" class="blog-post-tag">{тег}</a>' for тег in теги])}
        </div>
        
        <!-- Блок подписки на Telegram канал -->
        <footer class="blog-subscribe-footer">
            <div class="blog-subscribe-container">
                <div class="blog-subscribe-content">
                    <h3 class="blog-subscribe-title">Больше тренировок и мотивации</h3>
                    <p class="blog-subscribe-description">Подписывайся на наш Telegram-канал <strong>TABATA TIMER</strong> и получай ежедневные программы тренировок, таймеры и советы по фитнесу</p>
                    <div class="blog-subscribe-buttons">
                        <a href="https://t.me/fitnesstimer" target="_blank" rel="noopener noreferrer" class="blog-subscribe-button blog-subscribe-button-primary" onclick="if(typeof ym !== 'undefined'){{ym(42580049, 'reachGoal', 'blogSubscribeTelegram');}}">
                            Подписаться на канал
                        </a>
                        <a href="https://tabatatimer.ru/#timer" class="blog-subscribe-button blog-subscribe-button-secondary" onclick="if(typeof ym !== 'undefined'){{ym(42580049, 'reachGoal', 'blogToTimer');}}">
                            Открыть таймер
                        </a>
                    </div>
                </div>
            </div>
        </footer>
    </div>
    
    <!-- Burger Menu Script -->
    <script src="../assets/js/burger-menu.js"></script>
</body>
</html>"""
    
    return html, slug, изображение

def обновить_sitemap():
    """Обновляет sitemap.xml со всеми статьями блога"""
    if not BLOG_POSTS_FILE.exists():
        return
    
    with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    посты = data.get('posts', [])
    
    # Читаем существующий sitemap или создаём новый
    sitemap_file = Path('../public_html/sitemap.xml')
    sitemap_entries = []
    
    if sitemap_file.exists():
        # Парсим существующий sitemap (упрощённо)
        with open(sitemap_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Извлекаем существующие URL (кроме блог-постов)
            import re
            urls = re.findall(r'<loc>(https://www\.tabatatimer\.ru/[^<]+)</loc>', content)
            for url in urls:
                if '/blog/' not in url:  # Исключаем старые блог-посты
                    sitemap_entries.append(url)
    
    # Добавляем главную страницу и блог, если их нет
    if 'https://www.tabatatimer.ru/' not in sitemap_entries:
        sitemap_entries.insert(0, 'https://www.tabatatimer.ru/')
    if 'https://www.tabatatimer.ru/blog.html' not in sitemap_entries:
        sitemap_entries.append('https://www.tabatatimer.ru/blog.html')
    
    # Добавляем все посты блога
    for пост in посты:
        post_id = пост.get('id', 'unknown')
        заголовок = пост.get('title', 'Статья')
        slug = создать_slug(заголовок, post_id)
        url = f"https://www.tabatatimer.ru/blog/{slug}.html"
        if url not in sitemap_entries:
            sitemap_entries.append(url)
    
    # Генерируем sitemap.xml
    sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
'''
    
    for url in sitemap_entries:
        # Определяем приоритет и частоту обновления
        if url == 'https://www.tabatatimer.ru/':
            priority = '1.0'
            changefreq = 'daily'
        elif '/blog/' in url:
            priority = '0.8'
            changefreq = 'weekly'
        else:
            priority = '0.7'
            changefreq = 'monthly'
        
        sitemap_xml += f'''   <url>
      <loc>{url}</loc>
      <changefreq>{changefreq}</changefreq>
      <priority>{priority}</priority>
   </url>
'''
    
    sitemap_xml += '</urlset>'
    
    # Сохраняем sitemap
    with open(sitemap_file, 'w', encoding='utf-8') as f:
        f.write(sitemap_xml)
    
    print(f"✅ Sitemap обновлён ({len(sitemap_entries)} URL)")

def сгенерировать_страницы_для_всех_постов():
    """Генерирует HTML страницы для всех постов в blog-posts.json"""
    if not BLOG_POSTS_FILE.exists():
        print("❌ Файл blog-posts.json не найден")
        return
    
    with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    посты = data.get('posts', [])
    print(f"📝 Найдено постов: {len(посты)}")

    # Сбрасываем кеши slug для корректной уникальности
    SLUG_CACHE.clear()
    USED_SLUGS.clear()
    
    сгенерировано = 0
    обновления_изображений = {}  # post_id -> URL главного изображения (для списка блога)
    for пост in посты:
        try:
            html, slug, изображение_использовано = сгенерировать_html_страницу(пост)
            файл = BLOG_POSTS_DIR / f"{slug}.html"
            
            with open(файл, 'w', encoding='utf-8') as f:
                f.write(html)
            
            обновления_изображений[пост.get('id')] = изображение_использовано
            сгенерировано += 1
            print(f"✅ Создана страница: {slug}.html")
        except Exception as e:
            print(f"❌ Ошибка создания страницы для поста {пост.get('id', 'unknown')}: {e}")
    
    # Сохраняем blog-posts.json, если менялись post.image / порядок images (рецепты) или сверка с HTML
    json_dirty = any(пост.pop('_blog_json_dirty', False) for пост in data['posts'])
    if обновления_изображений:
        for пост in data['posts']:
            pid = пост.get('id')
            if pid and pid in обновления_изображений and пост.get('image') != обновления_изображений[pid]:
                пост['image'] = обновления_изображений[pid]
                json_dirty = True
    if json_dirty:
        with open(BLOG_POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("✅ blog-posts.json обновлён (превью/модалка и порядок фото для рецептов)")
    
    print(f"\n✅ Сгенерировано страниц: {сгенерировано}/{len(посты)}")
    
    # Загружаем все изображения блога в Yandex Cloud
    print("\n📤 Загружаю все изображения блога в Yandex Cloud...")
    try:
        загрузить_все_изображения_блога()
    except Exception as e:
        print(f"⚠️ Ошибка при загрузке изображений: {e}")
    
    # Обновляем sitemap
    обновить_sitemap()
    print("✅ Sitemap обновлён")

if __name__ == '__main__':
    сгенерировать_страницы_для_всех_постов()
