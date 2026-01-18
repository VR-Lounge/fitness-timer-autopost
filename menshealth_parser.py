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
from image_content_matcher import (
    выбрать_лучшее_изображение_для_контента,
    получить_использованные_изображения_из_постов
)
from text_cleaner import очистить_текст_для_telegram, очистить_текст_для_статьи
from topic_balance import выбрать_статью_для_баланса
from content_library import load_library
from telegram_dedup import is_duplicate as telegram_is_duplicate, record_post as telegram_record_post
from publication_logger import логировать_публикацию

# Импортируем функцию адаптации заголовка
try:
    from generate_blog_post_page import адаптировать_заголовок_для_русской_аудитории
except ImportError:
    # Если не удалось импортировать, создаём простую заглушку
    def адаптировать_заголовок_для_русской_аудитории(заголовок, текст=''):
        # Простая заглушка - возвращает как есть, если уже на русском
        if re.search(r'[а-яё]', заголовок, re.IGNORECASE):
            return заголовок
        return заголовок  # В реальности здесь должен быть перевод

# ============= КОНФИГУРАЦИЯ =============

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# Жёсткий анти-повтор для Telegram
TELEGRAM_ANTI_REPEAT_COUNT = int(os.getenv('TELEGRAM_ANTI_REPEAT_COUNT', '30'))

def получить_кандидаты_из_библиотеки(лимит=20):
    """Берёт лучшие статьи из библиотеки для публикации (только menshealth)."""
    library = load_library()
    items = library.get("items", [])
    items = [i for i in items if i.get("source") == "menshealth"]
    items = sorted(
        items,
        key=lambda x: (x.get("relevance_score", 0), x.get("fetched_at", "")),
        reverse=True
    )
    кандидаты = []
    for item in items:
        if len(кандидаты) >= лимит:
            break
        url = item.get("url", "")
        if not url or уже_обработана(url):
            continue
        if not item.get("images"):
            continue
        кандидаты.append({
            "title": item.get("title", ""),
            "link": url,
            "rss_feed_url": item.get("rss_feed_url", ""),
            "description": "",
            "keywords": item.get("keywords", [])
        })
    return кандидаты

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
    # 'https://www.healthpartners.com/blog/topic/mens-health/feed/',  # Ошибка парсинга XML (удалено)
    'https://danielawilson80.wordpress.com/feed/',
    'https://drtanmenshealthblog.com/feed/',
    'https://edsafecure.com/feed/',
    # 21-30
    'https://www.coachweb.com/feeds.xml',
    'https://drtracygapin.com/feed/',
    # 'https://www.belmarrahealth.com/mens-health/feed/',  # Ошибка парсинга XML (удалено)
    'https://ghc.health/blogs/all-about-men.atom',
    'https://youngmenshealthsite.org/feed/',
    # 'https://www.yourhealth.net.au/articles/category/family-health/mens-health/feed/',  # Ошибка парсинга XML (удалено)
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
    'https://www.menshealth.com/uk/fitness/cardio-exercise/',
    
    # НОВЫЕ ВЫСОКОРЕЛЕВАНТНЫЕ ФИДЫ (добавлены после тестирования, 80%+ релевантность)
    # ТОП-ПРИОРИТЕТ (100% релевантность)
    'https://www.muscleandfitness.com/feed/',  # Muscle & Fitness - бодибилдинг, силовые тренировки, питание, добавки, HIIT
    'https://www.nerdfitness.com/feed/',  # Nerd Fitness - фитнес для "ботаников", похудение, набор мышц, мотивация
    'https://barbend.com/feed/',  # BarBend - силовые виды спорта, CrossFit, тяжелая атлетика, пауэрлифтинг
    # 'https://hiitscience.com/feed',  # УДАЛЕНО: источник содержит только подкасты, не релевантен для блога
    'https://drjohnrusin.com/feed/',  # Dr. John Rusin - спортивная медицина, силовые, профилактика травм
    'https://fitdadchris.com/feed/',  # Fit Dad Chris - фитнес для пап, мотивация, тренировки
    'https://bengreenfieldlife.com/article/feed/',  # Ben Greenfield Life - биохакинг, спортивное питание, триатлон, оптимизация
    'https://www.bornfitness.com/feed/',  # Born Fitness - научный подход, питание, тренировки без BS
    'https://www.mensfitclub.com/mens-fitness/feed/',  # MensFitClub.com - комьюнити для мужчин, фитнес-новости, опыт
    'https://www.focusfitness.in/feed/',  # Focus Fitness - оборудование, советы, индийский рынок
    
    # ВЫСОКАЯ РЕЛЕВАНТНОСТЬ (80% релевантность)
    'https://www.mensfitness.com/.rss/feed/5a4c1162-86c8-4b99-8611-d683873db65d.xml',  # Men's Fitness - тренировки, планы для мужчин, советы, питание, стратегии
    'https://feeds.feedburner.com/volt-blog',  # Volt Athletics Blog - S&C для спорта, силовая подготовка, питание
    
    # НОВЫЕ ВЫСОКОРЕЛЕВАНТНЫЕ ФИДЫ (добавлены после проверки, 90-100% релевантность)
    'https://www.jimwendler.com/blogs/jimwendler-com.atom',  # Jim Wendler - автор 5/3/1, силовой тренинг, 90% релевантность
    'https://www.westside-barbell.com/blogs/the-blog.atom',  # Westside Barbell - легендарный пауэрлифтинг-клуб Луи Симмонса, 100% релевантность
]

# ЧЕРНЫЙ СПИСОК: URL статей, которые НЕ должны использоваться
BLACKLISTED_ARTICLE_URLS = [
    'https://hiitscience.com/the-mental-taper-the-biggest-mistake-athletes-make-with-dr-scott-frey-and-dr-martin-buchheit/',
    'hiitscience.com/the-mental-taper',  # Частичное совпадение
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

# Ограничение частоты публикации для источников (в днях)
# Источники, которые публикуются слишком часто, будут ограничены
SOURCE_PUBLICATION_LIMITS = {
    'hiitscience.com': 7,  # Не чаще 1 раза в 7 дней
    'training science': 7,  # Не чаще 1 раза в 7 дней
    'the training science podcast': 7,  # Не чаще 1 раза в 7 дней
}

# ============= ПРОМПТЫ ДЛЯ DEEPSEEK (ОПТИМИЗИРОВАНЫ ДЛЯ CACHE HIT) =============
# System prompts вынесены в константы для максимального кэширования
# Эти промпты будут кэшироваться при каждом запросе, экономя до 90% стоимости

SYSTEM_PROMPT_TELEGRAM = """Ты крутой фитнес-эксперт, который пишет посты для Telegram канала про TABATA, HIIT, интервальные тренировки и фитнес. Твой стиль - разговорный, как с лучшим другом/подругой.

КРИТИЧЕСКИ ВАЖНО:
- МАКСИМАЛЬНАЯ ДЛИНА: 900 символов (включая эмодзи и пробелы) - для Telegram caption с фото
- ВСЯ программа тренировки/диеты должна поместиться (упражнения, подходы, повторения, советы)
- Стиль: разговорный русский, как с другом, можно сленг, профессиональные термины из фитнеса
- Без воды: только суть, ёмко, по делу, интересно
- Мотивируй: добавь энергии, иногда шутки, но строго по делу
- Адаптация: для русского менталитета, понятные примеры"""

SYSTEM_PROMPT_ARTICLE = """Ты крутой фитнес-эксперт и копирайтер, который пишет полноценные статьи для блога о фитнесе, здоровье и тренировках. Твой стиль - разговорный, но информативный, как с опытным тренером.

КРИТИЧЕСКИ ВАЖНО:
- ДЛИНА: 2000-4000 символов - полноценная статья для сайта
- Стиль: разговорный русский, но с профессиональными терминами
- Структура: введение, основная часть с деталями, практические советы, заключение
- Адаптация: для русского менталитета, понятные примеры
- Без воды: только полезная информация, но развернуто
- Мотивируй: добавь энергии, но профессионально"""

# Шаблоны для user prompts (повторяющаяся часть будет кэшироваться)
USER_TEMPLATE_TELEGRAM = """Перепиши эту статью для Telegram поста (МАКСИМУМ 900 символов!):

ЗАГОЛОВОК: {заголовок}

ТЕКСТ:
{текст}

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

КРИТИЧЕСКИ ВАЖНО - НЕ ДОБАВЛЯЙ AI-МАРКЕРЫ:
- НЕ используй звёздочки *** для выделения
- НЕ используй хештеги # в тексте
- НЕ используй ## для заголовков (только обычный текст)
- НЕ используй маркдаун-синтаксис (**, __, и т.д.)
- Пиши как обычный человек, без формата разметки
- Текст должен выглядеть естественно, как написанный человеком

ПОМНИ: Максимум 900 символов, но ВСЯ программа должна быть! Текст должен выглядеть естественно, без AI-маркеров!"""

USER_TEMPLATE_ARTICLE = """Расширь и перепиши эту статью для полноценной статьи на сайте (2000-4000 символов):

ЗАГОЛОВОК: {заголовок}

ОРИГИНАЛЬНЫЙ ТЕКСТ:
{текст}

ТРЕБОВАНИЯ:
1. Полностью перепиши своими словами, убери ВСЕ следы источника
2. Расширь контент: добавь больше деталей, объяснений, практических советов
3. Структура статьи:
   - Введение (почему это важно)
   - Основная часть (детальное описание, программы, упражнения)
   - Практические советы
   - Как использовать таймер tabatatimer.ru
   - Заключение (мотивация)
4. Разговорный стиль: как с опытным тренером, можно сленг, профессиональные термины
5. Информативно: больше деталей, объяснений, но без воды
6. Мотивируй: энергия, но профессионально
7. В конце обязательно: как использовать таймер tabatatimer.ru (TABATA/EMOM/HIIT/AMRAP) для этой программы
8. Эмодзи: умеренно, для структуры
9. ДЛИНА: 2000-4000 символов - полноценная статья!

ПРИМЕР СВЯЗИ С ТАЙМЕРОМ:
"🔥 Для этой программы используй режим EMOM на tabatatimer.ru - каждую минуту новое упражнение из списка по кругу. Всего 5 раундов! Таймер — твой главный тренер здесь."

ПОМНИ: Это полноценная статья для сайта, не короткий пост! Расширь контент, добавь деталей, но сохрани разговорный стиль!"""

# Файл для хранения постов блога (будет синхронизироваться с сайтом)
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
                    'pub_date': pub_date,
                    'rss_feed_url': rss_url  # Сохраняем URL RSS фида для ротации источников
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

def получить_последние_использованные_источники(n=4):
    """
    Получает последние n использованных источников (RSS фиды и домены) из blog-posts.json
    для ротации источников RSS - чтобы не использовать один и тот же источник повторно
    
    Returns:
        dict с ключами:
        - 'rss_feeds': список URL RSS фидов, которые использовались в последних n постах
        - 'domains': список доменов, которые использовались в последних n постах
    """
    from urllib.parse import urlparse
    
    последние_rss_фиды = []
    последние_домены = []
    
    if not BLOG_POSTS_FILE.exists():
        return {'rss_feeds': последние_rss_фиды, 'domains': последние_домены}
    
    try:
        with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            посты = data.get('posts', [])
        
        # Получаем RSS фиды и домены из последних n постов
        for пост in посты[:n]:
            # Проверяем RSS фид (если сохранён)
            rss_feed_url = пост.get('rss_feed_url') or ''
            if rss_feed_url and rss_feed_url not in последние_rss_фиды:
                последние_rss_фиды.append(rss_feed_url)
            
            # Также получаем домен из source_url для дополнительной проверки
            источник_url = пост.get('source_url') or пост.get('url') or ''
            if источник_url:
                try:
                    домен = urlparse(источник_url).netloc.lower()
                    if домен and домен not in последние_домены:
                        последние_домены.append(домен)
                except:
                    pass
        
        return {'rss_feeds': последние_rss_фиды, 'domains': последние_домены}
    except Exception as e:
        print(f"⚠️ Ошибка получения последних источников: {e}")
        return {'rss_feeds': [], 'domains': []}

def проверить_ограничение_частоты_публикации(статья_url, источник):
    """Проверяет, не превышена ли частота публикации для источника"""
    from datetime import datetime, timedelta
    from urllib.parse import urlparse
    
    # Извлекаем домен из URL статьи
    try:
        parsed_url = urlparse(статья_url)
        домен = parsed_url.netloc.lower()
    except:
        домен = ''
    
    # Проверяем, есть ли ограничение для этого источника
    ограничение_дней = None
    найденный_ключ = None
    for ключ, дни in SOURCE_PUBLICATION_LIMITS.items():
        if ключ.lower() in домен or ключ.lower() in источник.lower():
            ограничение_дней = дни
            найденный_ключ = ключ
            break
    
    if ограничение_дней is None:
        return True, None  # Нет ограничения
    
    # Загружаем существующие посты
    if not BLOG_POSTS_FILE.exists():
        return True, None
    
    try:
        with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            посты = data.get('posts', [])
        
        # Проверяем последние публикации из этого источника
        текущая_дата = datetime.now()
        последние_публикации = []
        
        for пост in посты:
            пост_источник = пост.get('source', '').lower()
            пост_url = пост.get('url', '')
            
            # Проверяем, относится ли пост к этому источнику
            пост_домен = ''
            if пост_url:
                try:
                    пост_домен = urlparse(пост_url).netloc.lower()
                except:
                    pass
            
            if (найденный_ключ.lower() in пост_источник or 
                найденный_ключ.lower() in домен or
                найденный_ключ.lower() in пост_домен):
                
                # Получаем дату публикации
                дата_публикации = None
                if 'date' in пост:
                    try:
                        дата_публикации = datetime.fromisoformat(пост['date'].replace('Z', '+00:00'))
                    except:
                        if 'timestamp' in пост:
                            дата_публикации = datetime.fromtimestamp(пост['timestamp'])
                
                if дата_публикации:
                    # Убираем timezone для сравнения
                    if дата_публикации.tzinfo:
                        дата_публикации = дата_публикации.replace(tzinfo=None)
                    последние_публикации.append(дата_публикации)
        
        # Проверяем, есть ли публикации в пределах ограничения
        if последние_публикации:
            последняя_публикация = max(последние_публикации)
            разница_дней = (текущая_дата - последняя_публикация).days
            
            if разница_дней < ограничение_дней:
                return False, f"Источник '{найденный_ключ}' публиковался {разница_дней} дней назад (ограничение: {ограничение_дней} дней)"
        
        return True, None
    except Exception as e:
        print(f"⚠️ Ошибка проверки ограничения частоты публикации: {e}")
        return True, None  # В случае ошибки разрешаем публикацию

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
        
        # Извлекаем изображения с релевантной фильтрацией
        images = []  # Список словарей с url, alt, title
        
        # Ключевые слова для релевантности (фитнес, тренировки, питание)
        релевантные_ключевые_слова = [
            'workout', 'exercise', 'training', 'fitness', 'gym', 'cardio', 'strength',
            'nutrition', 'diet', 'food', 'meal', 'protein', 'carb', 'healthy',
            'tabata', 'hiit', 'emom', 'amrap', 'interval', 'training',
            'motivation', 'fitness', 'health', 'wellness', 'body', 'muscle',
            'workout', 'exercise', 'fitness', 'training', 'gym', 'sport'
        ]
        
        # Ключевые слова для исключения (реклама)
        рекламные_ключевые_слова = [
            'ad', 'advertisement', 'advert', 'promo', 'promotion', 'banner',
            'sponsor', 'sponsored', 'affiliate', 'affiliates', 'buy', 'shop',
            'sale', 'discount', 'offer', 'deal', 'click here', 'learn more'
        ]
        
        def изображение_релевантно(img_element, img_url):
            """Проверяет релевантность изображения по alt, title, src и классам"""
            # Получаем alt, title, src, классы
            alt = (img_element.get('alt') or '').lower()
            title_attr = (img_element.get('title') or '').lower()
            src_lower = img_url.lower()
            classes = ' '.join(img_element.get('class', [])).lower()
            parent_classes = ' '.join(img_element.find_parent().get('class', []) if img_element.find_parent() else []).lower()
            
            # Проверяем на рекламу
            текст_для_проверки = f"{alt} {title_attr} {src_lower} {classes} {parent_classes}"
            if any(рекламное_слово in текст_для_проверки for рекламное_слово in рекламные_ключевые_слова):
                return False
            
            # Проверяем на релевантность
            if any(релевантное_слово in текст_для_проверки for релевантное_слово in релевантные_ключевые_слова):
                return True
            
            # Если нет явных указаний, считаем релевантным если нет рекламных слов
            return not any(рекламное_слово in текст_для_проверки for рекламное_слово in рекламные_ключевые_слова)
        
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
            
            # Создаём объект изображения для главного
            images.append({
                'url': img_url,
                'alt': '',
                'title': '',
                'is_main': True
            })
        
        def извлечь_src_изображения(img_tag):
            """Извлекает URL изображения, включая srcset/data-srcset"""
            src = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-lazy-src') or img_tag.get('data-original')
            if not src:
                srcset = img_tag.get('srcset') or img_tag.get('data-srcset')
                if srcset:
                    src = srcset.split(',')[0].strip().split(' ')[0]
            return src
        
        def разрешенное_расширение(img_url):
            """Проверяет расширение файла по пути (без query)"""
            path = urlparse(img_url).path.lower()
            return any(path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif'])
        
        # Ищем изображения в статье
        article_images = soup.select('article img, .article-content img, .article-body img, main img, [class*="image"] img, [class*="photo"] img')
        for img in article_images[:40]:  # Увеличиваем до 40 изображений
            src = извлечь_src_изображения(img)
            if not src:
                continue
            
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
            
            # Фильтруем по расширению (учитываем query-параметры)
            if not разрешенное_расширение(src):
                continue
            
            # Проверяем релевантность
            if not изображение_релевантно(img, src):
                continue
            
            # Извлекаем alt и title
            alt = img.get('alt', '') or ''
            title_attr = img.get('title', '') or ''
            
            # Проверяем на дубликаты
            normalized = src.split('?')[0]
            if any(img_dict['url'].split('?')[0] == normalized for img_dict in images):
                continue
            
            images.append({
                'url': src,
                'alt': alt,
                'title': title_attr,
                'is_main': False
            })

        # Ищем изображения в <source> (picture/video)
        source_tags = soup.select('article source, .article-content source, .article-body source, main source')
        for source in source_tags[:40]:
            src = source.get('src') or None
            if not src:
                srcset = source.get('srcset') or source.get('data-srcset')
                if srcset:
                    src = srcset.split(',')[0].strip().split(' ')[0]
            if not src:
                continue
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                parsed = urlparse(url)
                src = f"{parsed.scheme}://{parsed.netloc}{src}"
            elif not src.startswith('http'):
                src = urljoin(url, src)
            if not разрешенное_расширение(src):
                continue
            images.append({
                'url': src,
                'alt': '',
                'title': '',
                'is_main': False
            })

        # Ищем background-image в style атрибутах в пределах статьи
        for elem in soup.select('article [style], .article-content [style], .article-body [style], main [style]'):
            style = elem.get('style', '')
            if 'background-image' not in style:
                continue
            match = re.findall(r'url\\(([^)]+)\\)', style)
            for raw in match:
                bg = raw.strip(' "\'')
                if not bg:
                    continue
                if bg.startswith('//'):
                    bg = 'https:' + bg
                elif bg.startswith('/'):
                    parsed = urlparse(url)
                    bg = f"{parsed.scheme}://{parsed.netloc}{bg}"
                elif not bg.startswith('http'):
                    bg = urljoin(url, bg)
                if not разрешенное_расширение(bg):
                    continue
                images.append({
                    'url': bg,
                    'alt': '',
                    'title': '',
                    'is_main': False
                })
        
        # Удаляем дубликаты по URL
        unique_images = []
        seen_urls = set()
        for img_dict in images:
            normalized = img_dict['url'].split('?')[0]
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                unique_images.append(img_dict)
        
        images = unique_images[:20]  # Оставляем до 20 релевантных изображений
        
        # Очищаем текст от лишних пробелов и переносов
        article_content = re.sub(r'\n{3,}', '\n\n', article_content)
        article_content = re.sub(r' {2,}', ' ', article_content)
        
        # Декодируем HTML entities
        article_content = html.unescape(article_content)
        
        return {
            'content': article_content[:5000],  # Ограничиваем длину
            'images': images  # Все релевантные изображения с alt и title
        }
    
    except Exception as e:
        print(f"❌ Ошибка парсинга статьи {url}: {e}")
        return None

def расширить_контент_для_статьи(оригинальный_текст, заголовок):
    """Делает расширенный рерайтинг для полноценной статьи на сайте (2000-4000 символов)"""
    if not DEEPSEEK_API_KEY:
        print("⚠️ DEEPSEEK_API_KEY не настроен, пропускаем расширение контента")
        return None
    
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        # Используем оптимизированные промпты для Cache HIT
        # System prompt кэшируется при каждом запросе (экономия 90%)
        system_prompt = SYSTEM_PROMPT_ARTICLE
        
        # User prompt использует шаблон (повторяющаяся часть кэшируется)
        user_prompt = USER_TEMPLATE_ARTICLE.format(
            заголовок=заголовок,
            текст=оригинальный_текст[:5000]
        )
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 3000,  # Больше токенов для расширенного контента
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.3
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=90)
        response.raise_for_status()
        
        result = response.json()
        расширенный_текст = result['choices'][0]['message']['content']
        
        # Очищаем текст от AI-маркеров
        расширенный_текст = очистить_текст_для_статьи(расширенный_текст)
        
        # Логируем использование кэша для мониторинга экономии
        usage = result.get('usage', {})
        cache_hit = usage.get('prompt_cache_hit_tokens', 0)
        cache_miss = usage.get('prompt_cache_miss_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        if cache_hit > 0:
            экономия_процент = (cache_hit / (cache_hit + cache_miss) * 100) if (cache_hit + cache_miss) > 0 else 0
            экономия_долларов = (cache_hit * 0.00028 - cache_hit * 0.000028)  # Разница в цене
            print(f"✅ Расширенный контент создан через DeepSeek ({len(расширенный_текст)} символов)")
            print(f"💚 Cache HIT: {cache_hit} токенов ({экономия_процент:.1f}%) | 💛 Cache MISS: {cache_miss} токенов | 💰 Экономия: ${экономия_долларов:.4f}")
        else:
            print(f"✅ Расширенный контент создан через DeepSeek ({len(расширенный_текст)} символов) | 💛 Cache MISS: {cache_miss} токенов (первый запрос или кэш сброшен)")
        
        return расширенный_текст
    
    except Exception as e:
        print(f"❌ Ошибка расширения контента через DeepSeek: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Ответ API: {e.response.text}")
        return None

def рерайтить_через_deepseek(оригинальный_текст, заголовок):
    """Делает качественный рерайтинг текста через DeepSeek AI для Telegram (900 символов)"""
    if not DEEPSEEK_API_KEY:
        print("⚠️ DEEPSEEK_API_KEY не настроен, пропускаем рерайтинг")
        return None
    
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        # Используем оптимизированные промпты для Cache HIT
        # System prompt кэшируется при каждом запросе (экономия 90%)
        system_prompt = SYSTEM_PROMPT_TELEGRAM
        
        # User prompt использует шаблон (повторяющаяся часть кэшируется)
        user_prompt = USER_TEMPLATE_TELEGRAM.format(
            заголовок=заголовок,
            текст=оригинальный_текст[:4000]
        )
        
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
        
        # Очищаем текст от AI-маркеров
        рерайт = очистить_текст_для_telegram(рерайт)
        
        # Логируем использование кэша для мониторинга экономии
        usage = result.get('usage', {})
        cache_hit = usage.get('prompt_cache_hit_tokens', 0)
        cache_miss = usage.get('prompt_cache_miss_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        if cache_hit > 0:
            экономия_процент = (cache_hit / (cache_hit + cache_miss) * 100) if (cache_hit + cache_miss) > 0 else 0
            экономия_долларов = (cache_hit * 0.00028 - cache_hit * 0.000028)  # Разница в цене
            print(f"✅ Рерайтинг выполнен через DeepSeek ({len(рерайт)} символов)")
            print(f"💚 Cache HIT: {cache_hit} токенов ({экономия_процент:.1f}%) | 💛 Cache MISS: {cache_miss} токенов | 💰 Экономия: ${экономия_долларов:.4f}")
        else:
            print(f"✅ Рерайтинг выполнен через DeepSeek ({len(рерайт)} символов) | 💛 Cache MISS: {cache_miss} токенов (первый запрос или кэш сброшен)")
        
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

def форматировать_пост(рерайт, оригинальный_заголовок, post_id=None, url=None):
    """Форматирует рерайт для публикации в Telegram с ссылкой на полную статью"""
    # Рерайт уже должен содержать связь с таймером и быть в пределах 900 символов
    # Хештеги не добавляем по требованию
    пост = рерайт
    
    # Добавляем ссылку на полную статью в конец поста
    # Используем переданный URL, если он есть, иначе создаём из заголовка
    url_статьи = None
    if url:
        url_статьи = url
    elif post_id and оригинальный_заголовок:
        slug = создать_slug(оригинальный_заголовок, post_id)
        url_статьи = f"https://www.tabatatimer.ru/blog/{slug}.html"
    
    if url_статьи:
        # Добавляем ссылку в HTML формате для Telegram
        ссылка_текст = f"\n\n📖 <a href=\"{url_статьи}\">Читать подробную статью →</a>"
        
        # Проверяем, не превысит ли это лимит в 1024 символа для caption
        if len(пост + ссылка_текст) <= 1024:
            пост += ссылка_текст
        else:
            # Если превышает, обрезаем пост, чтобы поместилась ссылка
            максимальная_длина_поста = 1024 - len(ссылка_текст)
            пост = пост[:максимальная_длина_поста].rstrip() + "..." + ссылка_текст
    
    return пост

def определить_теги(текст, заголовок, источник='menshealth'):
    """Улучшенная функция определения тегов на основе контента и источника"""
    теги = []
    текст_нижний = (текст + ' ' + заголовок).lower()
    заголовок_нижний = заголовок.lower()
    
    # ============= АУДИТОРИЯ (Мужчинам/Девушкам) =============
    мужская_аудитория = False
    женская_аудитория = False
    
    # Прямые указания
    if any(word in текст_нижний for word in ['мужчин', 'мужской', 'для парней', 'мужчинам', 'мужское', 'парням']):
        мужская_аудитория = True
    
    if any(word in текст_нижний for word in ['девушк', 'женщин', 'для девочек', 'девушкам', 'женский', 'для женщин', 'девушкам']):
        женская_аудитория = True
    
    # Контекстные признаки мужской аудитории
    мужские_маркеры = [
        'братан', 'брат',  # Обращение
        'твой кишечник', 'твой жкт', 'твой пресс', 'твой кишечник',  # Мужское обращение
        'набор массы', 'набираем массу', 'набрать массу', 'набор мышечной',  # Мужские цели
        'силовая тренировка', 'силовые тренировки', 'силовая',  # Силовые тренировки
        'простата', 'мужское здоровье', 'мужской жкт',  # Мужское здоровье
        'тестостерон',  # Мужские гормоны
        'брэндон', 'тренер',  # Мужской контекст
        'для мужчин', 'мужчина',  # Явные указания
    ]
    
    if any(маркер in текст_нижний for маркер in мужские_маркеры):
        мужская_аудитория = True
    
    # Контекстные признаки женской аудитории
    женские_маркеры = [
        'подруга', 'девочки',  # Обращение
        'стройное тело', 'похудеть', 'для девушек', 'для женщин',  # Женские цели
        'женское здоровье', 'женский',  # Женское здоровье
        'девушкам', 'девушка',  # Явные указания
    ]
    
    if any(маркер in текст_нижний for маркер in женские_маркеры):
        женская_аудитория = True
    
    # Если источник menshealth - по умолчанию для мужчин (если нет явных указаний на женскую аудиторию)
    if источник == 'menshealth' and not женская_аудитория:
        мужская_аудитория = True
    
    # Если источник womenshealth - по умолчанию для женщин (если нет явных указаний на мужскую аудиторию)
    if источник == 'womenshealth' and not мужская_аудитория:
        женская_аудитория = True
    
    # Проверка заголовка
    if any(word in заголовок_нижний for word in ['мужской', 'мужчин', 'мужск', 'для мужчин']):
        мужская_аудитория = True
    
    if any(word in заголовок_нижний for word in ['девушк', 'женщин', 'для девушек', 'женск']):
        женская_аудитория = True
    
    if мужская_аудитория:
        теги.append('Мужчинам')
    
    if женская_аудитория:
        теги.append('Девушкам')
    
    # ============= ПИТАНИЕ =============
    питание_маркеры = [
        'рецепт', 'питани', 'еда', 'блюд', 'продукт', 'ингредиент',
        'жкт', 'кишечник', 'желудок', 'пищеварен', 'желудочно-кишечн',
        'белок', 'углевод', 'жир', 'клетчатка', 'воды', 'водой',
        'завтрак', 'обед', 'ужин', 'перекус', 'меню', 'рацион',
        'витамин', 'минерал', 'протеин', 'макро', 'микро',
        'овощ', 'фрукт', 'мясо', 'рыба', 'яйцо', 'молочн',
        'питание мужчинам', 'для мужчин питание', 'мужское питание',
        'до тренировки', 'после тренировки', 'белки для роста'
    ]
    
    if any(маркер in текст_нижний for маркер in питание_маркеры):
        теги.append('Питание')
    
    # ============= ДИЕТЫ =============
    диеты_маркеры = [
        'диет', 'похуден', 'калори', 'дефицит калори', 'профицит',
        'кето', 'палео', 'вегетариан', 'веган', 'средиземноморск',
        'потеря веса', 'сброс веса', 'снижение веса',
        'бжу', 'баланс', 'макрос', 'микрос',
        'диета мужчинам', 'для мужчин диета', 'мужская диета'
    ]
    
    if any(маркер in текст_нижний for маркер in диеты_маркеры):
        теги.append('Диеты')
    
    # ============= МОТИВАЦИЯ =============
    мотивация_маркеры = [
        'мотивац', 'вдохнов', 'мотивир', 'результат', 'цель', 'успех',
        'философия', 'система', 'принцип', 'лайфхак', 'совет',
        'начни', 'начинай', 'не откладывай', 'сегодня',
        'сила в', 'мотивация', 'вдохновение', 'мотивировать',
        'психологи', 'ментальн', 'настрой', 'мышление',
        'мотивация мужчинам', 'для мужчин мотивация', 'мужская мотивация'
    ]
    
    if any(маркер in текст_нижний for маркер in мотивация_маркеры):
        теги.append('Мотивация')
    
    # ============= ТРЕНИРОВКА =============
    тренировка_маркеры = [
        'тренировк', 'упражнен', 'программа тренировок', 'программа',
        'подход', 'повторен', 'раунд', 'серия', 'цикл',
        'бурпи', 'приседан', 'отжиман', 'планка', 'выпад',
        'скручиван', 'планка', 'вакуум', 'присед', 'жим',
        'тяга', 'бицепс', 'трицепс', 'пресс', 'ягодиц',
        'табата', 'hiit', 'emom', 'amrap', 'интервал',
        'силовой', 'кардио', 'гимнастик', 'фитнес',
        'разминка', 'заминка', 'растяжка',
        'упражнения мужчинам', 'тренировки мужчинам', 'для мужчин тренировка',
        'силовая тренировка', 'набор массы', 'набрать массу'
    ]
    
    if any(маркер in текст_нижний for маркер in тренировка_маркеры):
        теги.append('Тренировка')
    
    # ============= СИЛОВЫЕ ТРЕНИРОВКИ =============
    силовые_маркеры = [
        'силовые тренировки', 'силовой тренинг', 'силовая подготовка',
        'weight training', 'strength training', 'силовые',
        'жим лёжа', 'присед со штангой', 'становая тяга',
        'barbell', 'штанга', 'гантели', 'dumbbell',
        'powerlifting', 'пауэрлифтинг', 'сила',
        '5/3/1', 'wendler', 'westside', 'conjugate',
        'max effort', 'dynamic effort', 'repetition effort',
        'силовой тренинг', 'силовая работа', 'работа с весом'
    ]
    
    if any(маркер in текст_нижний for маркер in силовые_маркеры):
        теги.append('Силовые')
    
    # ============= БОДИБИЛДИНГ =============
    бодибилдинг_маркеры = [
        'бодибилдинг', 'bodybuilding', 'набор мышечной массы',
        'гипертрофия', 'hypertrophy', 'мышечная масса',
        'набор массы', 'набрать массу', 'рост мышц',
        'split', 'сплит', 'бодибилдинг программа',
        'bodybuilding', 'бодибилдинг тренировка',
        'мышечный рост', 'набор веса', 'масса'
    ]
    
    if any(маркер in текст_нижний for маркер in бодибилдинг_маркеры):
        теги.append('Бодибилдинг')
    
    # ============= ПАУЭРЛИФТИНГ =============
    пауэрлифтинг_маркеры = [
        'пауэрлифтинг', 'powerlifting', 'сила',
        'жим', 'присед', 'тяга', 'big three',
        '1rm', 'одноповторный максимум', 'максимальный вес',
        'powerlifting', 'пауэрлифтинг программа',
        'conjugate', 'westside', 'сила'
    ]
    
    if any(маркер in текст_нижний for маркер in пауэрлифтинг_маркеры):
        теги.append('Пауэрлифтинг')
    
    # ============= КРОССФИТ =============
    кроссфит_маркеры = [
        'кроссфит', 'crossfit', 'wod', 'workout of the day',
        'функциональный тренинг', 'functional training',
        'кроссфит тренировка', 'crossfit workout',
        'функционалка', 'functional', 'кроссфит программа'
    ]
    
    if any(маркер in текст_нижний for маркер in кроссфит_маркеры):
        теги.append('Кроссфит')
    
    # ============= ФУНКЦИОНАЛЬНЫЙ ТРЕНИНГ =============
    функциональный_маркеры = [
        'функциональный тренинг', 'functional training',
        'функциональные движения', 'functional movement',
        'функционалка', 'functional', 'двигательные паттерны',
        'movement patterns', 'функциональная подготовка',
        'functional fitness', 'функциональный фитнес'
    ]
    
    if any(маркер in текст_нижний for маркер in функциональный_маркеры):
        теги.append('Функциональный тренинг')
    
    # Если тегов нет, добавляем по умолчанию
    if not теги:
        теги.append('Мотивация')
    
    return теги

def сохранить_пост_в_блог(текст, изображение_url, заголовок, источник='menshealth', расширенный_текст=None, все_изображения=None, post_id=None, url_статьи=None, rss_feed_url=None):
    """Сохраняет пост в JSON файл для блога с проверкой уникальности
    
    Args:
        текст: короткий текст для Telegram (900 символов)
        изображение_url: URL главного изображения
        заголовок: заголовок статьи
        источник: источник статьи
        расширенный_текст: расширенный текст для полноценной статьи на сайте (2000-4000 символов)
        все_изображения: список всех релевантных изображений из статьи (список словарей с url, alt, title)
    """
    try:
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Уникальность контента (ФОТО+ТЕКСТ)
        print("\n🔍 Проверка уникальности контента...")
        
        # Загружаем существующие посты для проверки семантической схожести
        существующие_посты = []
        if BLOG_POSTS_FILE.exists():
            with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                существующие_посты = data.get('posts', [])
        
        # Проверяем полную уникальность (с учётом заголовка и URL источника для обнаружения дубликатов)
        url_статьи = статья.get('link', '')
        уникален, причина = проверить_полную_уникальность(текст, изображение_url, существующие_посты, заголовок, url_статьи)
        
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
        
        # КРИТИЧЕСКИ ВАЖНО: Адаптируем заголовок на русский ДО сохранения
        # Используем расширенный текст для лучшей адаптации
        текст_для_адаптации = расширенный_текст if расширенный_текст else текст
        заголовок_русский = адаптировать_заголовок_для_русской_аудитории(заголовок, текст_для_адаптации)
        print(f"📝 Заголовок адаптирован: '{заголовок}' → '{заголовок_русский}'")
        
        # Определяем теги (используем русский заголовок)
        теги = определить_теги(текст, заголовок_русский, источник)
        
        # Скачиваем и загружаем изображения в Yandex Cloud
        if not post_id:
            post_id = f"{источник}_{int(time.time())}"
        print(f"\n📥 Скачиваю изображения для блога...")
        
        # КРИТИЧЕСКИ ВАЖНО: Получаем список уже использованных изображений из других постов
        использованные_изображения = получить_использованные_изображения_из_постов(существующие_посты)
        print(f"🔍 Проверяю уникальность изображений (уже используется {len(использованные_изображения)} изображений в других постах)")
        
        # Используем DeepSeek AI для выбора лучшего изображения, соответствующего контенту
        текст_для_анализа = расширенный_текст if расширенный_текст else текст
        лучшее_изображение = None
        
        if все_изображения:
            print(f"\n🤖 Анализирую {len(все_изображения)} изображений через DeepSeek AI для выбора лучшего...")
            лучшее_изображение = выбрать_лучшее_изображение_для_контента(
                все_изображения,
                заголовок_русский,
                текст_для_анализа,
                использованные_изображения
            )
        
        # В жёстком режиме не используем fallback изображений
        if not лучшее_изображение:
            print("❌ Нет подходящего изображения после строгого фильтра")
            return False
        
        # Обрабатываем главное изображение (выбранное через DeepSeek или из RSS)
        локальное_изображение_url = None
        изображение_для_скачивания = None
        
        if лучшее_изображение:
            изображение_для_скачивания = лучшее_изображение.get('url', '')
        elif изображение_url:
            изображение_для_скачивания = изображение_url
        
        if изображение_для_скачивания:
            # Проверяем, не используется ли это изображение в других постах
            normalized_url = изображение_для_скачивания.split('?')[0].lower()
            используется = any(
                normalized_url == existing_url.split('?')[0].lower()
                for existing_url in использованные_изображения
            )
            
            if используется:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Изображение уже используется в другом посте!")
                print(f"   URL: {изображение_для_скачивания[:80]}")
                print(f"   ⚠️ Пропускаю этот пост - нужно найти уникальное изображение")
                return False
            
            # Получаем список использованных изображений для проверки уникальности
            все_использованные_urls = получить_использованные_изображения_из_постов(существующие_посты)
            
            локальное_изображение_url = скачать_и_загрузить_изображение(
                изображение_для_скачивания, 
                post_id,
                заголовок=заголовок_русский,
                текст=расширенный_текст[:1000] if расширенный_текст else '',
                теги=теги,
                использованные_urls=все_использованные_urls,
                строгий_фильтр=True
            )
            if not локальное_изображение_url:
                print("❌ Нет подходящего изображения для публикации (жёсткий фильтр)")
                return False
        
        # Обрабатываем все релевантные изображения для галереи (исключая уже использованные)
        обработанные_изображения = []
        if все_изображения:
            print(f"\n📸 Обрабатываю {len(все_изображения)} изображений для галереи...")
            уникальные_для_галереи = []
            
            for img_dict in все_изображения[:10]:  # Ограничиваем до 10 изображений
                img_url = img_dict.get('url', '')
                if not img_url:
                    continue
                
                # Проверяем уникальность
                normalized_url = img_url.split('?')[0].lower()
                используется = any(
                    normalized_url == existing_url.split('?')[0].lower()
                    for existing_url in использованные_изображения
                )
                
                if not используется:
                    уникальные_для_галереи.append(img_dict)
            
            print(f"  ✅ Найдено {len(уникальные_для_галереи)} уникальных изображений для галереи")
            
            for idx, img_dict in enumerate(уникальные_для_галереи):
                img_url = img_dict.get('url', '')
                
                # Скачиваем и загружаем в Yandex Cloud
                img_post_id = f"{post_id}_{idx}"
                print(f"  📥 Скачиваю изображение {idx + 1}/{len(уникальные_для_галереи)}: {img_url[:60]}...")
                # Получаем список использованных изображений для проверки уникальности
                все_использованные_urls = получить_использованные_изображения_из_постов(существующие_посты)
                
                локальное_img_url = скачать_и_загрузить_изображение(
                    img_url, 
                    img_post_id,
                    заголовок=заголовок_русский,
                    текст=расширенный_текст[:1000] if расширенный_текст else '',
                    теги=теги,
                    использованные_urls=все_использованные_urls,
                    строгий_фильтр=True
                )
                if not локальное_img_url:
                    print(f"  ❌ Изображение {idx + 1} отклонено (жёсткий фильтр)")
                    continue
                print(f"  ✅ Изображение {idx + 1} загружено: {локальное_img_url[:60]}...")
                
                # Сохраняем изображение с alt и title (используем русский заголовок)
                обработанные_изображения.append({
                    'url': локальное_img_url,
                    'alt': img_dict.get('alt', '') or f"{заголовок_русский} - фото {idx + 1}",
                    'title': img_dict.get('title', '') or f"{заголовок_русский} - изображение {idx + 1}",
                    'is_main': img_dict.get('is_main', False) and idx == 0
                })
            
            print(f"✅ Обработано {len(обработанные_изображения)} изображений для галереи")
        
        # Если нет обработанных изображений, используем главное изображение
        if not обработанные_изображения and локальное_изображение_url:
            обработанные_изображения.append({
                'url': локальное_изображение_url,
                'alt': f"{заголовок_русский} - фото тренировки и фитнеса",
                'title': f"{заголовок_русский} - профессиональное фото тренировки",
                'is_main': True
            })
        
        # Используем расширенный текст для блога, если он есть, иначе короткий текст
        текст_для_блога = расширенный_текст if расширенный_текст else текст
        
        # Создаём slug и URL на основе русского заголовка
        slug = создать_slug(заголовок_русский, post_id)
        url = f"https://www.tabatatimer.ru/blog/{slug}.html"
        print(f"🔗 Создан URL: {url}")
        
        # Создаём новый пост (с русским заголовком и URL)
        новый_пост = {
            'id': post_id,
            'title': заголовок_русский,  # Сохраняем русский заголовок
            'text': текст_для_блога,  # Используем расширенный текст для полноценной статьи
            'image': локальное_изображение_url,  # Главное изображение (для обратной совместимости)
            'images': обработанные_изображения,  # Все релевантные изображения с alt и title
            'tags': теги,
            'source': источник,
            'source_url': url_статьи or '',  # Сохраняем URL исходной статьи для ротации источников
            'rss_feed_url': rss_feed_url or '',  # Сохраняем URL RSS фида для ротации источников
            'date': datetime.now().isoformat(),
            'timestamp': int(time.time()),
            'url': url  # КРИТИЧЕСКИ ВАЖНО: Сохраняем URL сразу
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
        
        # КРИТИЧЕСКИ ВАЖНО: Генерируем HTML страницу СРАЗУ после сохранения в JSON
        # Это гарантирует, что страница будет создана ДО отправки в Telegram
        print(f"\n📄 Генерирую HTML страницу для статьи...")
        try:
            генератор = Path(__file__).parent / 'generate_blog_post_page.py'
            if генератор.exists():
                # Увеличиваем timeout до 60 секунд для больших статей
                result = subprocess.run(
                    ['python3', str(генератор)],
                    cwd=str(Path(__file__).parent),
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    print("✅ HTML страница для статьи сгенерирована")
                    # Проверяем, что файл действительно создан
                    html_file = REPO_ROOT / 'public_html' / 'blog' / f"{slug}.html"
                    if html_file.exists():
                        print(f"✅ HTML файл подтверждён: {html_file.name}")
                    else:
                        print(f"⚠️ HTML файл не найден: {html_file.name}")
                else:
                    print(f"❌ Ошибка генерации HTML страницы: {result.stderr}")
                    print(f"   stdout: {result.stdout}")
                    # НЕ возвращаем False - пост уже сохранён, просто нет HTML
            else:
                print(f"⚠️ Файл generate_blog_post_page.py не найден: {генератор}")
        except subprocess.TimeoutExpired:
            print(f"⚠️ Таймаут генерации HTML страницы (превышено 60 секунд)")
        except Exception as e:
            print(f"⚠️ Ошибка генерации HTML страницы: {e}")
            import traceback
            traceback.print_exc()
        
        # Возвращаем URL для использования в Telegram
        return {'success': True, 'url': url, 'title': заголовок_русский}
    
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
    уже_обработанных = 0
    не_релевантных = 0
    
    # Получаем последние использованные источники для ротации
    последние_источники = получить_последние_использованные_источники(4)  # Последние 4 источника
    последние_rss_фиды = последние_источники.get('rss_feeds', [])
    последние_домены = последние_источники.get('domains', [])
    print(f"🔄 Ротация источников: исключаем последние {len(последние_rss_фиды)} RSS фидов и {len(последние_домены)} доменов")
    
    for статья in все_статьи:
        url_статьи = статья['link']
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Черный список URL статей
        if any(blacklisted in url_статьи.lower() for blacklisted in BLACKLISTED_ARTICLE_URLS):
            print(f"🚫 Статья в черном списке: {url_статьи[:60]}...")
            не_релевантных += 1
            continue
        
        if уже_обработана(url_статьи):
            уже_обработанных += 1
            continue
        
        # Проверяем ограничение частоты публикации для источника
        источник = url_статьи
        можно_публиковать, причина_ограничения = проверить_ограничение_частоты_публикации(источник, источник)
        if not можно_публиковать:
            print(f"⏭️ Пропущена статья из-за ограничения частоты: {причина_ограничения}")
            не_релевантных += 1
            continue
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Ротация источников - не используем последние 3-4 источника
        # Проверяем RSS фид статьи (если сохранён)
        rss_feed_статьи = статья.get('rss_feed_url', '')
        if rss_feed_статьи and rss_feed_статьи in последние_rss_фиды:
            print(f"🔄 Пропущена статья из недавно использованного RSS фида: {rss_feed_статьи[:60]}...")
            не_релевантных += 1
            continue
        
        # Также проверяем домен источника
        домен_источника = urlparse(url_статьи).netloc.lower() if url_статьи else ''
        if домен_источника in последние_домены:
            print(f"🔄 Пропущена статья из недавно использованного домена: {домен_источника}")
            не_релевантных += 1
            continue
        
        релевантна, ключевые_слова = проверить_релевантность(статья)
        if релевантна:
            статья['keywords'] = ключевые_слова
            релевантные.append(статья)
        else:
            не_релевантных += 1
    
    print(f"✅ Релевантных статей: {len(релевантные)}")
    if уже_обработанных > 0:
        print(f"⚠️ Уже обработано статей: {уже_обработанных}")
    if не_релевантных > 0:
        print(f"⚠️ Не релевантных статей: {не_релевантных}")
    
    if not релевантные:
        print("ℹ️ Нет новых релевантных статей для обработки")
        return
    
    # УЛУЧШЕНИЕ: Выбираем статью с лучшим балансом тематик
    текущий_час_utc = datetime.utcnow().strftime('%H')
    print(f"\n🎯 Выбор статьи с учетом баланса тематик (текущее время: {текущий_час_utc}:00 UTC)...")
    
    # Выбираем статью для баланса из первых 20 релевантных
    выбранная_статья = выбрать_статью_для_баланса(релевантные[:20], текущий_час_utc, n_анализируемых=10)
    
    # Если не удалось выбрать по балансу, используем первую релевантную
    if not выбранная_статья and релевантные:
        print("⚠️ Не удалось выбрать статью по балансу, используем первую релевантную")
        выбранная_статья = релевантные[0]
    
    # Обрабатываем статьи до тех пор, пока не найдём уникальный контент с качественными фото
    обработано = 0
    максимальное_количество_попыток = min(40, len(релевантные))  # Ищем качественный контент среди большего числа статей
    
    # Сначала берём кандидатов из библиотеки, потом — из RSS
    статьи_из_библиотеки = получить_кандидаты_из_библиотеки(лимит=20)
    статьи_для_обработки = статьи_из_библиотеки + релевантные
    статьи_для_обработки = статьи_для_обработки[:максимальное_количество_попыток]
    
    # Если выбрали статью по балансу, ставим её первой в списке
    if выбранная_статья and выбранная_статья in статьи_для_обработки:
        # Перемещаем выбранную статью в начало списка
        статьи_для_обработки.remove(выбранная_статья)
        статьи_для_обработки.insert(0, выбранная_статья)
        print(f"✅ Приоритет: статья выбрана по балансу тематик")
    
    for i, статья in enumerate(статьи_для_обработки):
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
        
        # Рерайтинг через DeepSeek для Telegram (короткий)
        print("\n🤖 Рерайтинг для Telegram через DeepSeek AI...")
        рерайт_telegram = рерайтить_через_deepseek(parsed['content'], статья['title'])
        
        if not рерайт_telegram:
            print("❌ Не удалось выполнить рерайтинг, пробуем следующую...\n")
            continue
        
        # Расширенный рерайтинг для полноценной статьи на сайте
        print("\n📝 Расширение контента для полноценной статьи...")
        расширенный_текст = расширить_контент_для_статьи(parsed['content'], статья['title'])
        
        # Если расширение не удалось, используем короткий текст
        if not расширенный_текст:
            print("⚠️ Не удалось расширить контент, используем короткий текст")
            расширенный_текст = None
        
        # Создаём post_id заранее, чтобы можно было добавить ссылку в пост
        post_id = f"menshealth_{int(time.time())}"
        
        # Получаем все релевантные изображения
        все_изображения = parsed['images']  # Список словарей с url, alt, title
        
        # Выбираем главное изображение для Telegram (первое или помеченное как главное)
        главное_изображение = None
        for img_dict in все_изображения:
            if img_dict.get('is_main', False):
                главное_изображение = img_dict
                break
        if not главное_изображение and все_изображения:
            главное_изображение = все_изображения[0]
        
        фото_url = главное_изображение['url'] if главное_изображение else None
        
        # Проверяем, нужно ли публиковать на сайт (с HTML страницей)
        публиковать_на_сайт = os.getenv('PUBLISH_TO_BLOG', 'false').lower() == 'true'
        
        if публиковать_на_сайт:
            # ПРОВЕРКА УНИКАЛЬНОСТИ ПЕРЕД СОХРАНЕНИЕМ В БЛОГ
            print("\n🔍 Проверка уникальности перед сохранением в блог...")
            результат_сохранения = сохранить_пост_в_блог(рерайт_telegram, фото_url, статья['title'], 'menshealth', расширенный_текст, все_изображения, post_id=post_id, url_статьи=статья['link'], rss_feed_url=статья.get('rss_feed_url', ''))
            
            # Проверяем результат (может быть False или dict с success/url/title)
            if not результат_сохранения or (isinstance(результат_сохранения, dict) and not результат_сохранения.get('success')):
                print("⚠️ Контент не уникален, пробуем следующую статью...\n")
                # Сохраняем как обработанную, чтобы не пытаться снова
                сохранить_обработанную_статью(статья['link'])
                continue
            
            # Извлекаем URL и русский заголовок из результата
            if isinstance(результат_сохранения, dict):
                url_статьи = результат_сохранения.get('url', '')
                заголовок_русский = результат_сохранения.get('title', статья['title'])
            else:
                # Обратная совместимость (старый формат возврата)
                url_статьи = ''
                заголовок_русский = статья['title']
        else:
            # Только Telegram, не сохраняем в блог
            print("\n📱 Режим: только Telegram (без публикации на сайт)")
            url_статьи = ''
            заголовок_русский = адаптировать_заголовок_для_русской_аудитории(статья['title'], расширенный_текст if расширенный_текст else рерайт_telegram)
        
        # Форматируем пост с ссылкой (если есть) и отправляем в Telegram
        print("\n📤 Отправка в Telegram...")
        пост = форматировать_пост(рерайт_telegram, заголовок_русский, post_id=post_id, url=url_статьи if публиковать_на_сайт else None)
        
        # ЖЁСТКИЙ АНТИ-ПОВТОР: проверяем текст и изображение перед отправкой
        if TELEGRAM_ANTI_REPEAT_COUNT > 0 and telegram_is_duplicate(пост, фото_url, TELEGRAM_ANTI_REPEAT_COUNT):
            print("❌ Анти‑повтор: текст/картинка уже публиковались в Telegram, пробуем следующую статью...\n")
            continue
        
        успех_telegram = отправить_в_telegram(пост, фото_url)
        
        if успех_telegram:
            telegram_record_post(пост, фото_url, TELEGRAM_ANTI_REPEAT_COUNT)
            # Сохраняем как обработанную
            сохранить_обработанную_статью(статья['link'])
            обработано += 1
            
            # ЛОГИРОВАНИЕ: Сохраняем информацию о публикации
            теги = определить_теги(рерайт_telegram, заголовок_русский, 'menshealth')
            аудитория = 'Мужчинам' if 'Мужчинам' in теги else 'Девушкам' if 'Девушкам' in теги else 'Неизвестно'
            
            логировать_публикацию({
                'date': datetime.now().isoformat(),
                'time': datetime.utcnow().strftime('%H:%M:%S UTC'),
                'audience': аудитория,
                'tags': теги,
                'source_rss': статья.get('link', ''),
                'publish_to_blog': публиковать_на_сайт,
                'publish_to_telegram': True,
                'title': заголовок_русский,
                'post_id': post_id,
                'url': url_статьи if публиковать_на_сайт else None,
                'image_url': фото_url
            })
            
            print(f"\n✅ Статья успешно обработана и опубликована!")
            break  # Успешно обработали, выходим
        else:
            print(f"\n❌ Ошибка отправки в Telegram, пробуем следующую...\n")
            # Не сохраняем как обработанную, чтобы попробовать снова позже
    
    if обработано == 0:
        print(f"\n⚠️ Не удалось обработать ни одну статью (все были дубликатами или ошибки)")

if __name__ == '__main__':
    главная()
