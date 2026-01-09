#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Парсер статей из Men's Health с рерайтингом через DeepSeek AI
    
    Парсит RSS фид menshealth.com, фильтрует статьи по темам
    (TABATA, HIIT, AMRAP, EMOM, интервальные тренировки, диеты),
    делает качественный рерайтинг через DeepSeek и публикует в Telegram.
    
    Автор: VR-Lounge
    Канал: @fitnesstimer
"""

import os
import requests
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import time
import html
import sys
import subprocess

# Добавляем путь к модулю проверки уникальности
sys.path.insert(0, str(Path(__file__).parent))
from content_uniqueness import (
    проверить_полную_уникальность,
    сохранить_контент_как_использованный
)
from image_downloader import скачать_и_загрузить_изображение

# ============= КОНФИГУРАЦИЯ =============

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# RSS фиды Men's Health (40+ источников)
MENSHEALTH_RSS_FEEDS = [
    # 1-10
    'https://www.theturekclinic.com/feed/',
    'https://tamh.menshealthnetwork.org/feed/',
    'https://www.swaggermagazine.com/feed/',
    'https://menalive.com/feed/',
    'https://www.artofmanliness.com/health-fitness/feed/',
    'https://goodmenproject.com/category/health/feed/',
    'https://guycounseling.com/category/mens-blog/feed/',
    'https://www.news-medical.net/category/Mens-Health-News.aspx/feed/feed/feeds/posts/default',
    'https://lostempireherbs.com/category/mens-health/feed/',
    'https://www.ahchealthenews.com/category/mens-health/feed/',
    # 11-20
    'https://www.hippocraticpost.com/category/mens-health/feed/',
    'https://www.mensfitclub.com/feed/',
    'https://drardyceyik.com/category/mens-health/feed/',
    'https://www.menshealth.com/rss/all.xml/',
    'https://thehealthcast.com/category/mens-health/feed/',
    'https://vitaljake.com/feed/',
    'https://www.healthpartners.com/blog/topic/mens-health/feed/',
    'https://danielawilson80.wordpress.com/feed/',
    'https://drtanmenshealthblog.com/feed/',
    'https://edsafecure.com/feed/',
    # 21-30
    'https://www.coachweb.com/feeds.xml',
    'https://drtracygapin.com/feed/',
    'https://www.belmarrahealth.com/mens-health/feed/',
    'https://ghc.health/blogs/all-about-men.atom',
    'https://youngmenshealthsite.org/feed/',
    'https://www.yourhealth.net.au/articles/category/family-health/mens-health/feed/',
    'https://www.mazemenshealth.com/blog/feed/',
    'https://www.charlottemenshealth.com/feed/',
    'https://feeds.feedburner.com/Insureblog',
    'https://malehealth.org.au/blog/feed/',
    # 31-40
    'https://www.relaxedmale.com/category/mens-health/feed/',
    'https://aballsysenseoftumor.com/feed/',
    'https://www.optimummenshealth.com/blog/feed/',
    'http://best-natural-health-fitness-blogs.blogspot.com/feeds/posts/default?alt=rss',
    'https://olivierhealthtips.com/feed/?x=1',
    'https://www.timrobinsoncounsellor.com/blog-feed.xml',
    'https://mensvariety.com/category/wellness/feed/',
    'https://anabolicmen.com/feed/',
    'https://www.buygenericpills.com/blog/feed/',
    # Дополнительные проверенные источники
    'https://www.menshealth.com/uk/rss/all.xml/',
    'https://www.menshealth.com/uk/workouts/',
    'https://www.menshealth.com/uk/nutrition/',
    'https://www.menshealth.com/uk/fitness/',
    'https://www.menshealth.com/uk/fitness/cardio-exercise/'
]

# Ключевые слова для фильтрации статей
RELEVANT_KEYWORDS = [
    # Интервальные тренировки
    'tabata', 'hiit', 'amrap', 'emom', 'interval training', 'interval workout',
    'high intensity', 'circuit training', 'timed workout', 'workout timer',
    # Диеты и питание
    'diet', 'nutrition', 'meal plan', 'protein', 'carb', 'calorie',
    'weight loss', 'fat loss', 'metabolism', 'meal prep',
    # Упражнения и тренировки
    'workout', 'exercise', 'training', 'fitness', 'cardio', 'strength',
    'endurance', 'conditioning', 'burn fat', 'build muscle',
    # Связанные темы
    'quick workout', 'home workout', 'bodyweight', 'no equipment',
    'short workout', 'efficient workout', 'effective training'
]

# Файл для хранения обработанных статей (чтобы не дублировать)
PROCESSED_ARTICLES_FILE = Path('.menshealth_processed.json')

# Файл для хранения постов блога (будет синхронизироваться с сайтом)
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

# ============= ФУНКЦИИ ПАРСИНГА =============

def загрузить_обработанные_статьи():
    """Загружает список уже обработанных статей"""
    if PROCESSED_ARTICLES_FILE.exists():
        try:
            with open(PROCESSED_ARTICLES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {'articles': [], 'last_update': None}
    return {'articles': [], 'last_update': None}

def сохранить_обработанную_статью(article_url):
    """Сохраняет URL обработанной статьи"""
    data = загрузить_обработанные_статьи()
    if article_url not in data['articles']:
        data['articles'].append(article_url)
        data['last_update'] = datetime.now().isoformat()
        # Ограничиваем размер (храним последние 1000 статей)
        if len(data['articles']) > 1000:
            data['articles'] = data['articles'][-1000:]
        with open(PROCESSED_ARTICLES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def уже_обработана(article_url):
    """Проверяет, была ли статья уже обработана"""
    data = загрузить_обработанные_статьи()
    return article_url in data['articles']

def парсить_rss_feed(rss_url):
    """Парсит RSS фид и возвращает список статей"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(rss_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Парсим XML
        root = ET.fromstring(response.content)
        articles = []
        
        # Обрабатываем элементы <item>
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            link_elem = item.find('link')
            description_elem = item.find('description')
            pub_date_elem = item.find('pubDate')
            
            if title_elem is not None and link_elem is not None:
                title = title_elem.text or ''
                link = link_elem.text or ''
                description = description_elem.text if description_elem is not None else ''
                pub_date = pub_date_elem.text if pub_date_elem is not None else ''
                
                articles.append({
                    'title': title,
                    'link': link,
                    'description': description,
                    'pub_date': pub_date
                })
        
        print(f"✅ Получено {len(articles)} статей из {rss_url}")
        return articles
    
    except Exception as e:
        print(f"❌ Ошибка парсинга RSS {rss_url}: {e}")
        return []

def проверить_релевантность(article):
    """Проверяет, релевантна ли статья по ключевым словам"""
    text_to_check = f"{article['title']} {article['description']}".lower()
    
    # Проверяем наличие ключевых слов
    matches = []
    for keyword in RELEVANT_KEYWORDS:
        if keyword.lower() in text_to_check:
            matches.append(keyword)
    
    # Если найдено хотя бы 2 ключевых слова - статья релевантна
    return len(matches) >= 2, matches

def парсить_статью(url):
    """Парсит полный текст статьи и изображения с сайта menshealth.com"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Извлекаем основной текст статьи
        # Ищем основной контент (обычно в <article> или <div class="article-content">)
        article_content = None
        
        # Пробуем разные селекторы
        selectors = [
            'article',
            '.article-content',
            '.article-body',
            '[class*="article"]',
            '[class*="content"]',
            'main'
        ]
        
        for selector in selectors:
            content = soup.select_one(selector)
            if content:
                # Удаляем ненужные элементы (реклама, навигация и т.д.)
                for unwanted in content.select('script, style, nav, aside, .ad, .advertisement, .social-share'):
                    unwanted.decompose()
                article_content = content.get_text(separator='\n', strip=True)
                break
        
        if not article_content:
            # Если не нашли структурированный контент, берем весь body
            body = soup.find('body')
            if body:
                for unwanted in body.select('script, style, nav, aside, header, footer, .ad, .advertisement'):
                    unwanted.decompose()
                article_content = body.get_text(separator='\n', strip=True)
        
        # Извлекаем изображения
        images = []
        
        # Ищем главное изображение (обычно в <meta property="og:image">)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image['content']
            # Преобразуем относительные URL в абсолютные
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                img_url = 'https://www.menshealth.com' + img_url
            elif not img_url.startswith('http'):
                img_url = urljoin(url, img_url)
            images.append(img_url)
        
        # Ищем изображения в статье
        article_images = soup.select('article img, .article-content img, .article-body img, main img, [class*="image"] img, [class*="photo"] img')
        for img in article_images[:10]:  # Берем первые 10 изображений для выбора лучшего
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
            if src:
                # Преобразуем относительные URL в абсолютные
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://www.menshealth.com' + src
                elif not src.startswith('http'):
                    src = urljoin(url, src)
                
                # Фильтруем маленькие изображения (иконки, аватары и т.д.)
                width = img.get('width') or img.get('data-width')
                height = img.get('height') or img.get('data-height')
                if width and height:
                    try:
                        if int(width) < 200 or int(height) < 200:
                            continue  # Пропускаем маленькие изображения
                    except (ValueError, TypeError):
                        pass
                
                # Фильтруем по расширению
                if any(src.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    if src not in images:
                        images.append(src)
        
        # Удаляем дубликаты и оставляем только уникальные URL
        unique_images = []
        seen = set()
        for img_url in images:
            # Нормализуем URL (убираем параметры для сравнения)
            normalized = img_url.split('?')[0]
            if normalized not in seen:
                seen.add(normalized)
                unique_images.append(img_url)
        
        images = unique_images[:3]  # Берем первые 3 уникальных изображения
        
        # Очищаем текст от лишних пробелов и переносов
        article_content = re.sub(r'\n{3,}', '\n\n', article_content)
        article_content = re.sub(r' {2,}', ' ', article_content)
        
        # Декодируем HTML entities
        article_content = html.unescape(article_content)
        
        return {
            'content': article_content[:5000],  # Ограничиваем длину
            'images': images[:3]  # Берем первые 3 изображения
        }
    
    except Exception as e:
        print(f"❌ Ошибка парсинга статьи {url}: {e}")
        return None

def рерайтить_через_deepseek(оригинальный_текст, заголовок):
    """Делает качественный рерайтинг текста через DeepSeek AI"""
    if not DEEPSEEK_API_KEY:
        print("⚠️ DEEPSEEK_API_KEY не настроен, пропускаем рерайтинг")
        return None
    
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        # Промпт для рерайтинга
        system_prompt = """Ты крутой фитнес-эксперт, который пишет посты для Telegram канала про TABATA, HIIT, интервальные тренировки и фитнес. Твой стиль - разговорный, как с лучшим другом/подругой.

КРИТИЧЕСКИ ВАЖНО:
- МАКСИМАЛЬНАЯ ДЛИНА: 900 символов (включая эмодзи и пробелы) - для Telegram caption с фото
- ВСЯ программа тренировки/диеты должна поместиться (упражнения, подходы, повторения, советы)
- Стиль: разговорный русский, как с другом, можно сленг, профессиональные термины из фитнеса
- Без воды: только суть, ёмко, по делу, интересно
- Мотивируй: добавь энергии, иногда шутки, но строго по делу
- Адаптация: для русского менталитета, понятные примеры"""
        
        user_prompt = f"""Перепиши эту статью для Telegram поста (МАКСИМУМ 900 символов!):

ЗАГОЛОВОК: {заголовок}

ТЕКСТ:
{оригинальный_текст[:4000]}

ТРЕБОВАНИЯ:
1. Полностью перепиши своими словами, убери ВСЕ следы источника (menshealth.com, Men's Health)
2. ВСЯ программа тренировки/диеты должна поместиться (упражнения, подходы, повторения, советы)
3. Разговорный стиль: как с другом, можно сленг, профессиональные термины
4. Без воды: только суть, ёмко, интересно
5. Мотивируй: энергия, иногда шутки, но по делу
6. В конце обязательно: как использовать таймер tabatatimer.ru (TABATA/EMOM/HIIT/AMRAP) для этой программы
7. Эмодзи: умеренно, для структуры
8. МАКСИМУМ 900 СИМВОЛОВ! Но ВСЯ программа должна быть!

ПРИМЕР СВЯЗИ С ТАЙМЕРОМ:
"💪 Для этой программы используй режим EMOM на tabatatimer.ru - каждую минуту новое упражнение!"
или
"🔥 Запусти TABATA таймер на tabatatimer.ru и делай каждое упражнение 20 сек, отдых 10 сек!"

ПОМНИ: Максимум 900 символов, но ВСЯ программа должна быть!"""
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.8,  # Больше креативности для разговорного стиля
            "max_tokens": 1000,  # Ограничиваем для коротких постов
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.3
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        рерайт = result['choices'][0]['message']['content']
        
        print(f"✅ Рерайтинг выполнен через DeepSeek ({len(рерайт)} символов)")
        return рерайт
    
    except Exception as e:
        print(f"❌ Ошибка рерайтинга через DeepSeek: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Ответ API: {e.response.text}")
        return None

def отправить_в_telegram(текст, фото_url=None):
    """Отправляет пост с текстом и фото в Telegram канал"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не настроены")
        return False
    
    try:
        if фото_url:
            # Отправляем с фото
            # Telegram ограничивает caption для фото: максимум 1024 символа
            if len(текст) > 1024:
                # Обрезаем до 1000 символов, чтобы точно поместилось
                оригинальная_длина = len(текст)
                текст = текст[:1000]
                print(f"⚠️ Текст обрезан до {len(текст)} символов (было {оригинальная_длина} символов)")
                print(f"⚠️ ВНИМАНИЕ: Рерайт должен быть короче! Уменьши промпт для DeepSeek.")
            
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            params = {
                "chat_id": TELEGRAM_CHAT_ID,
                "photo": фото_url,
                "caption": текст,
                "parse_mode": "HTML"
            }
        else:
            # Отправляем только текст
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            params = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": текст,
                "parse_mode": "HTML"
            }
        
        response = requests.post(url, json=params, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if result.get('ok'):
            message_id = result['result'].get('message_id')
            print(f"✅ Пост отправлен в Telegram! Message ID: {message_id}")
            return True
        else:
            print(f"❌ Ошибка отправки в Telegram: {result}")
            return False
    
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Ответ API: {e.response.text}")
        return False

def форматировать_пост(рерайт, оригинальный_заголовок):
    """Форматирует рерайт для публикации в Telegram"""
    # Рерайт уже должен содержать связь с таймером и быть в пределах 900 символов
    # Хештеги не добавляем по требованию
    пост = рерайт
    
    return пост

def определить_теги(текст, заголовок):
    """Определяет теги поста на основе контента"""
    теги = []
    текст_нижний = (текст + ' ' + заголовок).lower()
    
    # Мужчинам
    if any(word in текст_нижний for word in ['мужчин', 'мужской', 'для парней', 'мужчинам']):
        теги.append('Мужчинам')
    
    # Питание
    if any(word in текст_нижний for word in ['рецепт', 'питани', 'еда', 'блюд', 'продукт', 'ингредиент']):
        теги.append('Питание')
    
    # Диеты
    if any(word in текст_нижний for word in ['диет', 'похуден', 'калори', 'белк', 'углевод', 'жир']):
        теги.append('Диеты')
    
    # Мотивация
    if any(word in текст_нижний for word in ['мотивац', 'вдохнов', 'мотивир', 'результат', 'цель', 'успех']):
        теги.append('Мотивация')
    
    # Если тегов нет, добавляем по умолчанию
    if not теги:
        теги.append('Мотивация')
    
    return теги

def сохранить_пост_в_блог(текст, изображение_url, заголовок, источник='menshealth'):
    """Сохраняет пост в JSON файл для блога с проверкой уникальности"""
    try:
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Уникальность контента (ФОТО+ТЕКСТ)
        print("\n🔍 Проверка уникальности контента...")
        
        # Загружаем существующие посты для проверки семантической схожести
        существующие_посты = []
        if BLOG_POSTS_FILE.exists():
            with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                существующие_посты = data.get('posts', [])
        
        # Проверяем полную уникальность
        уникален, причина = проверить_полную_уникальность(текст, изображение_url, существующие_посты)
        
        if not уникален:
            print(f"❌ Контент НЕ уникален: {причина}")
            print("⚠️ Пост НЕ будет сохранён в блог (дубликат контента)")
            return False
        
        print("✅ Контент уникален!")
        
        # Загружаем существующие посты для добавления
        if BLOG_POSTS_FILE.exists():
            with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {'posts': []}
        
        # Определяем теги
        теги = определить_теги(текст, заголовок)
        
        # Скачиваем и загружаем изображение в Yandex Cloud
        post_id = f"{источник}_{int(time.time())}"
        print(f"\n📥 Скачиваю изображение для блога...")
        локальное_изображение_url = скачать_и_загрузить_изображение(изображение_url, post_id)
        
        # Если не удалось скачать, используем оригинальный URL
        if not локальное_изображение_url or локальное_изображение_url == изображение_url:
            print(f"⚠️ Использую оригинальный URL изображения")
            локальное_изображение_url = изображение_url
        
        # Создаём новый пост
        новый_пост = {
            'id': post_id,
            'title': заголовок,
            'text': текст,
            'image': локальное_изображение_url,  # Используем URL из Yandex Cloud
            'tags': теги,
            'source': источник,
            'date': datetime.now().isoformat(),
            'timestamp': int(time.time())
        }
        
        # Добавляем в начало списка
        data['posts'].insert(0, новый_пост)
        
        # Ограничиваем количество постов (храним последние 500)
        if len(data['posts']) > 500:
            data['posts'] = data['posts'][:500]
        
        # Сохраняем
        BLOG_POSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BLOG_POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # ВАЖНО: Сохраняем контент как использованный (добавляем хеши)
        сохранить_контент_как_использованный(текст, изображение_url)
        
        print(f"✅ Пост сохранён в блог ({len(теги)} тегов: {', '.join(теги)})")
        
        # Генерируем HTML страницу для SEO
        try:
            генератор = Path(__file__).parent / 'generate_blog_post_page.py'
            if генератор.exists():
                result = subprocess.run(
                    ['python3', str(генератор)],
                    cwd=str(Path(__file__).parent),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    print("✅ HTML страница для статьи сгенерирована")
                else:
                    print(f"⚠️ Ошибка генерации HTML страницы: {result.stderr}")
        except Exception as e:
            print(f"⚠️ Ошибка генерации HTML страницы: {e}")
        
        return True
    
    except Exception as e:
        print(f"⚠️ Ошибка сохранения поста в блог: {e}")
        return False

# ============= ГЛАВНАЯ ФУНКЦИЯ =============

def главная():
    """Главная функция: парсит RSS, фильтрует, рерайтит и публикует"""
    print("=" * 60)
    print("🚀 ЗАПУСК ПАРСЕРА MEN'S HEALTH")
    print("=" * 60)
    
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DEEPSEEK_API_KEY]):
        print("❌ Не настроены переменные окружения:")
        print("   - TELEGRAM_BOT_TOKEN")
        print("   - TELEGRAM_CHAT_ID")
        print("   - DEEPSEEK_API_KEY")
        return
    
    # Загружаем список обработанных статей
    processed = загрузить_обработанные_статьи()
    print(f"📋 Уже обработано статей: {len(processed['articles'])}")
    
    # Парсим RSS фиды
    все_статьи = []
    for rss_url in MENSHEALTH_RSS_FEEDS:
        # Проверяем различные форматы RSS/Atom фидов
        if (rss_url.endswith('.xml') or 
            rss_url.endswith('.xml/') or
            rss_url.endswith('.atom') or 
            rss_url.endswith('/feed') or 
            rss_url.endswith('/feed/') or
            rss_url.endswith('?format=feed') or
            rss_url.endswith('?format=rss') or
            rss_url.endswith('?format=RSS') or
            '/feed' in rss_url or
            '/rss' in rss_url or
            '.xml' in rss_url or
            '.atom' in rss_url or
            'feedburner.com' in rss_url or
            'feeds/posts' in rss_url):
            try:
                # Это RSS фид
                статьи = парсить_rss_feed(rss_url)
                все_статьи.extend(статьи)
            except Exception as e:
                print(f"⚠️ Ошибка парсинга {rss_url}: {e}")
                continue
        else:
            # Это обычная страница - можно добавить парсинг HTML позже
            print(f"⏭️ Пропускаем HTML страницу: {rss_url}")
    
    # Удаляем дубликаты по URL
    уникальные_статьи = {}
    for статья in все_статьи:
        url = статья['link']
        if url not in уникальные_статьи:
            уникальные_статьи[url] = статья
    все_статьи = list(уникальные_статьи.values())
    
    print(f"\n📰 Всего получено статей: {len(все_статьи)}")
    
    # Фильтруем по релевантности
    релевантные = []
    for статья in все_статьи:
        if уже_обработана(статья['link']):
            continue
        
        релевантна, ключевые_слова = проверить_релевантность(статья)
        if релевантна:
            статья['keywords'] = ключевые_слова
            релевантные.append(статья)
    
    print(f"✅ Релевантных статей: {len(релевантные)}")
    
    if not релевантные:
        print("ℹ️ Нет новых релевантных статей для обработки")
        return
    
    # Обрабатываем релевантные статьи до тех пор, пока не найдём уникальный контент
    обработано = 0
    максимальное_количество_попыток = min(5, len(релевантные))  # Пробуем максимум 5 статей
    
    for i, статья in enumerate(релевантные[:максимальное_количество_попыток]):
        print(f"\n{'='*60}")
        print(f"📝 Попытка {i+1}/{максимальное_количество_попыток}: {статья['title']}")
        print(f"🔗 URL: {статья['link']}")
        print(f"🔑 Ключевые слова: {', '.join(статья['keywords'])}")
        print(f"{'='*60}\n")
        
        # Парсим полный текст и изображения
        print("📥 Парсинг статьи...")
        parsed = парсить_статью(статья['link'])
        
        if not parsed or not parsed['content']:
            print("❌ Не удалось получить контент статьи, пробуем следующую...\n")
            continue
        
        print(f"✅ Получен контент ({len(parsed['content'])} символов)")
        print(f"✅ Найдено изображений: {len(parsed['images'])}")
        
        if not parsed['images']:
            print("⚠️ Нет изображений, пробуем следующую статью...\n")
            continue
        
        # Рерайтинг через DeepSeek
        print("\n🤖 Рерайтинг через DeepSeek AI...")
        рерайт = рерайтить_через_deepseek(parsed['content'], статья['title'])
        
        if not рерайт:
            print("❌ Не удалось выполнить рерайтинг, пробуем следующую...\n")
            continue
        
        # Форматируем пост
        пост = форматировать_пост(рерайт, статья['title'])
        
        # Выбираем лучшее изображение
        фото_url = parsed['images'][0]
        
        # ПРОВЕРКА УНИКАЛЬНОСТИ ПЕРЕД СОХРАНЕНИЕМ
        print("\n🔍 Проверка уникальности перед сохранением...")
        успех_сохранения = сохранить_пост_в_блог(пост, фото_url, статья['title'], 'menshealth')
        
        if not успех_сохранения:
            print("⚠️ Контент не уникален, пробуем следующую статью...\n")
            # Сохраняем как обработанную, чтобы не пытаться снова
            сохранить_обработанную_статью(статья['link'])
            continue
        
        # Если контент уникален и сохранён, отправляем в Telegram
        print("\n📤 Отправка в Telegram...")
        успех_telegram = отправить_в_telegram(пост, фото_url)
        
        if успех_telegram:
            # Сохраняем как обработанную
            сохранить_обработанную_статью(статья['link'])
            обработано += 1
            print(f"\n✅ Статья успешно обработана и опубликована!")
            break  # Успешно обработали, выходим
        else:
            print(f"\n❌ Ошибка отправки в Telegram, пробуем следующую...\n")
            # Не сохраняем как обработанную, чтобы попробовать снова позже
    
    if обработано == 0:
        print(f"\n⚠️ Не удалось обработать ни одну статью (все были дубликатами или ошибки)")

if __name__ == '__main__':
    главная()
