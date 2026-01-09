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
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

# Путь к файлу с постами
# В GitHub Actions репозиторий клонируется в корень, поэтому используем относительный путь
SCRIPT_DIR = Path(__file__).parent.absolute()
# Проверяем, где мы находимся
if (SCRIPT_DIR.parent / 'public_html').exists():
    # Мы в fitness-timer-autopost, public_html на уровень выше
    REPO_ROOT = SCRIPT_DIR.parent
elif (SCRIPT_DIR / 'public_html').exists():
    # Мы в корне репозитория
    REPO_ROOT = SCRIPT_DIR
else:
    # Пробуем найти public_html относительно текущей директории
    REPO_ROOT = Path.cwd()
    if not (REPO_ROOT / 'public_html').exists():
        # Последняя попытка - ищем в родительской директории
        REPO_ROOT = REPO_ROOT.parent

BLOG_POSTS_FILE = REPO_ROOT / 'public_html' / 'blog-posts.json'
BLOG_POSTS_DIR = REPO_ROOT / 'public_html' / 'blog'
BLOG_POSTS_DIR.mkdir(parents=True, exist_ok=True)

def очистить_текст_от_html(текст):
    """Очищает текст от HTML тегов для мета-описания"""
    if not текст:
        return ''
    # Убираем HTML теги
    текст = re.sub(r'<[^>]+>', '', текст)
    # Убираем лишние пробелы
    текст = ' '.join(текст.split())
    return текст

def создать_slug(текст, post_id):
    """Создаёт URL-friendly slug из текста или использует ID"""
    if not текст:
        return post_id
    
    # Транслитерация и очистка
    транслит = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    
    текст = текст.lower()
    slug = ''
    for char in текст:
        if char in транслит:
            slug += транслит[char]
        elif char.isalnum() or char in '- ':
            slug += char
        else:
            slug += '-'
    
    # Очищаем и ограничиваем длину
    slug = re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')[:50]
    
    if not slug:
        slug = post_id
    
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
    """Создаёт уникальный alt и title для изображения"""
    вариации_alt = [
        f"{заголовок} - фото тренировки и фитнеса",
        f"Иллюстрация к статье: {заголовок}",
        f"Фото для статьи о {', '.join(теги[:2])}",
        f"Изображение: {заголовок} | TABATATIMER.RU",
        f"Фото тренировки: {заголовок}"
    ]
    
    вариации_title = [
        f"{заголовок} - профессиональное фото тренировки",
        f"Иллюстрация статьи о фитнесе: {заголовок}",
        f"Фото для материала: {заголовок}",
        f"Изображение статьи: {заголовок} | Блог TABATATIMER.RU",
        f"Фотография тренировки: {заголовок}"
    ]
    
    alt = вариации_alt[индекс % len(вариации_alt)]
    title = вариации_title[индекс % len(вариации_title)]
    
    # Добавляем уникальный идентификатор
    уникальный_суффикс = f" | ID: {hash(заголовок + str(индекс)) % 10000}"
    alt += уникальный_суффикс
    title += уникальный_суффикс
    
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

def форматировать_текст_для_html(текст, заголовок, теги):
    """Форматирует текст поста для HTML с уникальными ссылками и изображениями"""
    if not текст:
        return ''
    
    # Заменяем ссылки на tabatatimer.ru на уникальные ссылки с #timer
    def заменить_ссылку(match):
        url = match.group(1)
        # Если уже есть #timer, оставляем как есть
        if '#timer' in url:
            return url
        # Иначе добавляем #timer
        if url.endswith('/'):
            return url[:-1] + '#timer'
        else:
            return url + '#timer'
    
    # Применяем замену ссылок (только для простых URL без тегов)
    ссылка_паттерн = r'(https?://(?:www\.)?tabatatimer\.ru[^"\s]*)'
    текст = re.sub(ссылка_паттерн, заменить_ссылку, текст)
    
    # Находим все ссылки на tabatatimer.ru в HTML тегах <a> и заменяем их на уникальные
    ссылки_на_таймер = re.findall(r'<a[^>]*href=["\']([^"\']*tabatatimer\.ru[^"\']*)["\'][^>]*>([^<]*)</a>', текст, re.IGNORECASE)
    
    счётчик_ссылок = 0
    for url, текст_ссылки in ссылки_на_таймер:
        if 'tabatatimer.ru' in url.lower():
            новый_url = url.split('#')[0] + '#timer' if '#' not in url else url.replace(url.split('#')[1], 'timer')
            новый_текст, новый_title = создать_уникальную_ссылку_на_таймер(текст, теги, счётчик_ссылок)
            новая_ссылка = f'<a href="{новый_url}" target="_blank" rel="noopener noreferrer" title="{новый_title}">{новый_текст}</a>'
            текст = текст.replace(f'<a href="{url}">{текст_ссылки}</a>', новая_ссылка, 1)
            счётчик_ссылок += 1
    
    # Если в тексте нет ссылок на таймер, добавляем одну естественным образом
    if счётчик_ссылок == 0:
        # Ищем подходящее место для вставки ссылки (после первого абзаца или перед списком)
        текст_ссылки, title_ссылки = создать_уникальную_ссылку_на_таймер(текст, теги, 0)
        ссылка_html = f'<p><a href="https://www.tabatatimer.ru/#timer" target="_blank" rel="noopener noreferrer" title="{title_ссылки}">{текст_ссылки}</a> на <strong>tabatatimer.ru</strong> для максимальной эффективности тренировок.</p>'
        
        # Вставляем после первого абзаца
        первый_p = re.search(r'<p>', текст)
        if первый_p:
            позиция = первый_p.end()
            текст = текст[:позиция] + ссылка_html + текст[позиция:]
        else:
            # Если нет абзацев, добавляем в начало
            текст = ссылка_html + текст
    
    # Обрабатываем изображения - добавляем уникальные alt и title
    счётчик_изображений = 0
    def заменить_изображение(match):
        nonlocal счётчик_изображений
        полный_тег = match.group(0)
        alt, title = создать_уникальный_alt_для_изображения(заголовок, теги, счётчик_изображений)
        счётчик_изображений += 1
        
        # Если уже есть alt, заменяем его
        if 'alt=' in полный_тег:
            полный_тег = re.sub(r'alt=["\'][^"\']*["\']', f'alt="{alt}"', полный_тег)
        else:
            полный_тег = полный_тег.replace('<img', f'<img alt="{alt}"')
        
        # Если уже есть title, заменяем его
        if 'title=' in полный_тег:
            полный_тег = re.sub(r'title=["\'][^"\']*["\']', f'title="{title}"', полный_тег)
        else:
            полный_тег = полный_тег.replace('<img', f'<img title="{title}"')
        
        return полный_тег
    
    текст = re.sub(r'<img[^>]*>', заменить_изображение, текст, flags=re.IGNORECASE)
    
    return текст

def сгенерировать_html_страницу(пост):
    """Генерирует HTML страницу для поста"""
    post_id = пост.get('id', 'unknown')
    заголовок = пост.get('title', 'Статья')
    текст = пост.get('text', '')
    изображение = пост.get('image', 'https://www.tabatatimer.ru/images/og-image.jpg')
    теги = пост.get('tags', [])
    дата_публикации = пост.get('date', datetime.now().isoformat())
    timestamp = пост.get('timestamp', int(datetime.now().timestamp()))
    
    # Создаём slug для URL
    slug = создать_slug(заголовок, post_id)
    url = f"https://www.tabatatimer.ru/blog/{slug}.html"
    
    # Создаём уникальное описание для каждой статьи
    описание_текст = очистить_текст_от_html(текст)
    if описание_текст:
        # Берём первые 150 символов и добавляем уникальный суффикс
        описание = описание_текст[:150].strip()
        if len(описание_текст) > 150:
            описание += '...'
        # Добавляем уникальный идентификатор для полной уникальности
        уникальный_id = hash(заголовок + str(timestamp)) % 10000
        описание += f" | {', '.join(теги)} | ID: {уникальный_id}"
    else:
        описание = f"Статья о фитнесе, тренировках и здоровом образе жизни. {', '.join(теги)}. Уникальная программа тренировок."
    
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
    <meta name="keywords" content="{ключевые_слова}">
    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no" />
    <meta name="author" content="TABATATIMER.RU">
    <meta name="robots" content="index, follow">
    <meta name="language" content="Russian">
    <meta name="revisit-after" content="7 days">
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
        
        .blog-post-content {{
            line-height: 1.8;
            font-size: 1.1rem;
        }}
        
        .blog-post-content h2 {{
            font-size: 1.8rem;
            margin: 30px 0 15px 0;
            color: #7af5ff;
        }}
        
        .blog-post-content h3 {{
            font-size: 1.5rem;
            margin: 25px 0 12px 0;
            color: rgba(255, 255, 255, 0.9);
        }}
        
        .blog-post-content h4 {{
            font-size: 1.2rem;
            margin: 20px 0 10px 0;
            color: rgba(255, 255, 255, 0.85);
        }}
        
        .blog-post-content p {{
            margin: 0 0 15px 0;
        }}
        
        .blog-post-content ul,
        .blog-post-content ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        
        .blog-post-content li {{
            margin: 8px 0;
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
            color: #7af5ff;
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
        
        @media (max-width: 768px) {{
            .blog-post-title {{
                font-size: 1.8rem;
            }}
            
            .blog-post-page {{
                padding: 20px 15px;
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
        </div>
        
        <div class="blog-post-tags">
            {''.join([f'<span class="blog-post-tag">{тег}</span>' for тег in теги])}
        </div>
    </div>
    
    <!-- Burger Menu Script -->
    <script src="../assets/js/burger-menu.js"></script>
</body>
</html>"""
    
    return html, slug

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
    
    сгенерировано = 0
    for пост in посты:
        try:
            html, slug = сгенерировать_html_страницу(пост)
            файл = BLOG_POSTS_DIR / f"{slug}.html"
            
            with open(файл, 'w', encoding='utf-8') as f:
                f.write(html)
            
            сгенерировано += 1
            print(f"✅ Создана страница: {slug}.html")
        except Exception as e:
            print(f"❌ Ошибка создания страницы для поста {пост.get('id', 'unknown')}: {e}")
    
    print(f"\n✅ Сгенерировано страниц: {сгенерировано}/{len(посты)}")
    
    # Обновляем sitemap
    обновить_sitemap()

if __name__ == '__main__':
    сгенерировать_страницы_для_всех_постов()
