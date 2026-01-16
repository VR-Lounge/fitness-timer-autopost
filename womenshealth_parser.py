#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Парсер статей из Women's Health RSS фидов с рерайтингом через DeepSeek AI
    
    Парсит RSS фиды женских фитнес и здоровье ресурсов, фильтрует статьи по темам
    (TABATA, HIIT, AMRAP, EMOM, интервальные тренировки, диеты, женское здоровье),
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
from topic_balance import выбрать_статью_для_баланса
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

# RSS фиды Women's Health (40 проверенных рабочих источников)
WOMENSHEALTH_RSS_FEEDS = [
    # ПРИОРИТЕТ 1: ФИТНЕС, HIIT, TABATA, ТРЕНИРОВКИ (1-20)
    'https://hiitscience.com/feed',  # HIIT Science - научный подход к HIIT
    'https://nourishmovelove.com/feed/',  # Nourish Move Love - HIIT + домашние тренировки
    # 'https://www.girlsgonestrong.com/feed/',  # Girls Gone Strong - HTTP 403 (удалено)
    'https://gymbunny.ie/feed/',  # Gym Bunny - фитнес-коды, HIIT, диеты
    'https://www.womenfitness.net/feed/',  # Women Fitness - всё для женского фитнеса
    'https://fitnessista.com/feed/',  # The Fitnessista - домашние тренировки + HIIT
    'https://femalefitnesssystems.com/feed/',  # Female Fitness Systems - тренировки + питание
    # 'https://fitbottomedgirls.com/feed',  # Fit Bottomed Girls - HTTP 403 (удалено)
    'https://my.toneitup.com/blogs/latest.atom',  # Tone It Up - тренировки + мотивация
    'https://sarahfit.com/feed/',  # Sarah Fit - clean eating + тренировки
    # 'https://www.fit4females.com/fitblog/feed/',  # Fit4Females - HTTP 403 (удалено)
    'https://healthworksfitness.com/feed/',  # Healthworks Fitness - женское здоровье + фитнес
    'https://womensfitnessclubs.com/feed/',  # Womens Fitness Club - групповые тренировки
    'https://www.fitnessmag.co.za/feed/',  # Fitness Magazine (ЮАР) - женский фитнес-лайфстайл
    # 'https://www.stronghealthywoman.com/feed/',  # Strong Healthy Woman - Таймаут (удалено)
    'https://www.healthista.com/feed/',  # Healthista - здоровье + фитнес UK
    'https://femmephysiques.com/feed/',  # Femmephysiques - body confidence + тренировки
    'https://lazygirlfitness.com.au/feed/',  # Lazy Girl Fitness - простые тренировки
    # 'http://fitnessontoast.com/feed/',  # Fitness On Toast - HTTP 503 (удалено)
    'https://www.kaylainthecity.com/feed/',  # Kayla in the City - NYC фитнес-блогер
    
    # ПРИОРИТЕТ 2: ПИТАНИЕ, ДИЕТЫ, НУТРИЦИОЛОГИЯ (21-29)
    'https://jessicasepel.com/feed',  # JS Health - нутрициолог Jessica Sepel
    'https://www.sheknows.com/health-and-wellness/feed/',  # SheKnows Health & Wellness
    'https://www.healthywomen.org/feeds/feed.rss',  # HealthyWomen - женское здоровье
    'https://nourishinglab.com/feed/',  # Nourishing Lab - IBS, Hashimoto's, питание
    'https://www.fempower-health.com/blog-feed.xml',  # Fempower Health - PCOS, бесплодие, диеты
    'https://realmomnutrition.com/feed',  # Real Mom Nutrition - питание для мам
    'https://abbylangernutrition.com/feed',  # Abby Langer Nutrition - диетология
    'https://sharonpalmer.com/feed',  # Sharon Palmer - растительное питание
    'https://bebodywise.com/blog/rss/',  # Bodywise - женское здоровье + питание
    
    # ПРИОРИТЕТ 3: МОТИВАЦИЯ + ЛАЙФСТАЙЛ (30-37)
    'http://knocked-upfitness.com/feed/',  # Knocked-Up Fitness - фитнес для беременных
    'https://flecksoflex.com/feed/',  # The Sweat Fearlessly Podcast - фитнес, велнес, йога
    'https://www.jerseygirltalk.com/feed/',  # Jersey Girl Talk - фитнес + бьюти
    # 'https://amodrn.com/feed/',  # Amodrn - HTTP 403 (удалено)
    # 'https://www.besthealthmag.ca/wellness/health/feed/',  # Best Health Magazine - HTTP 403 (удалено)
    'http://www.livingbetter50.com/category/health-fitness/feed/',  # LivingBetter50 - для женщин 50+
    'https://sanitydaily.com/feed/',  # Sanity Daily - ментальное здоровье
    
    # ДОПОЛНИТЕЛЬНЫЕ СПЕЦИАЛИЗИРОВАННЫЕ (38-40)
    'https://bwhi.org/feed/',  # Black Women's Health Imperative
    'https://www.intimina.com/blog/feed/',  # Intimina - женское интимное здоровье
    # 'https://www.hormona.io/feed/',  # Hormona Library - HTTP 404 (удалено)
    'https://adriaticawomenshealth.com/newsblog/feed/',  # Adriatica Women's Health - женское здоровье
    
    # НОВЫЕ ПРОВЕРЕННЫЕ ФИДЫ (41-58) - добавлены после тестирования
    # ТОП-ПРИОРИТЕТ (100% релевантность)
    'https://skinnyms.com/category/fitness/feed/',  # Skinny Ms - программы тренировок, меню, фитнес-планы, HIIT
    'https://blog.myfitnesspal.com/feed/',  # MyFitnessPal Blog - похудение, питание, рецепты, фитнес, калории
    'https://www.nataliejillfitness.com/feed/',  # Natalie Jill Fitness - функциональные тренировки, похудение, безглютеновое питание
    'https://lauralondonfitness.com/feed/',  # Laura London Fitness - фитнес для мам 40+, трансформация тела, мотивация
    'https://www.behealthynow.co.uk/feed/',  # Be Healthy Now - здоровое питание, рецепты, питание, фитнес, натуральная красота
    'https://hipandhealthy.com/category/fitness/feed/',  # Hip & Healthy - фитнес-тренды, советы, технологии
    # 'https://artofhealthyliving.com/category/fitness/feed/',  # Art of Healthy Living - HTTP 403 (удалено)
    'https://www.bornfitness.com/feed/',  # Born Fitness - научный подход к фитнесу, питание, стратегии
    
    # ВЫСОКАЯ РЕЛЕВАНТНОСТЬ (80% релевантность)
    'https://fit4mom.com/blog?format=rss',  # FIT4MOM - фитнес до/после родов, тренировки для мам, велнес
    # 'https://fitgirlsdiary.com/feed/',  # Fit Girl's Diary - HTTP 403 (удалено)
    'https://www.healthifyme.com/blog/feed/',  # Healthifyme - похудение, трекинг питания, диеты, фитнес
    'https://www.muscleandfitness.com/feed/',  # Muscle & Fitness - силовые тренировки, питание, бодибилдинг
    
    # СРЕДНЯЯ РЕЛЕВАНТНОСТЬ (60-67% релевантность)
    'https://ellymcguinness.com/feed/',  # Elly McGuinness - холистик-фитнес, пренатальные тренировки, похудение
    'https://www.massyarias.com/feed/',  # Massy Arias - лайфстайл-медицина, тренировки, трансформация
    'https://www.carlyrowena.com/blog?format=rss',  # Carly Rowena - баланс, фитнес без жертв, мотивация
    'https://barbend.com/feed/',  # BarBend - CrossFit, тяжёлая атлетика, пауэрлифтинг, питание
    
    # НИЗКАЯ РЕЛЕВАНТНОСТЬ (40% релевантность, но рабочие)
    'https://lovesweatfitness.com/blogs/news.atom',  # Love Sweat Fitness - тренировки дома, программы, челленджи, рецепты, мотивация
    'https://gethealthyu.com/feed/',  # Get Healthy U - фитнес для женщин 40+, тренировки, питание, здоровый образ жизни
]

# Ключевые слова для фильтрации статей
RELEVANT_KEYWORDS = [
    # Интервальные тренировки
    'tabata', 'hiit', 'amrap', 'emom', 'interval training', 'interval workout',
    'high intensity', 'circuit training', 'timed workout', 'workout timer',
    # Диеты и питание
    'diet', 'nutrition', 'meal plan', 'protein', 'carb', 'calorie',
    'weight loss', 'fat loss', 'metabolism', 'meal prep', 'healthy eating',
    # Упражнения и тренировки
    'workout', 'exercise', 'training', 'fitness', 'cardio', 'strength',
    'endurance', 'conditioning', 'burn fat', 'build muscle', 'toning',
    # Женское здоровье
    'women health', 'female fitness', 'hormones', 'period', 'menstrual',
    'pregnancy workout', 'postpartum', 'menopause', 'women wellness',
    # Связанные темы
    'quick workout', 'home workout', 'bodyweight', 'no equipment',
    'short workout', 'efficient workout', 'effective training', 'yoga', 'pilates'
]

# Файл для хранения обработанных статей (чтобы не дублировать)
PROCESSED_ARTICLES_FILE = Path('.womenshealth_processed.json')

# ============= ПРОМПТЫ ДЛЯ DEEPSEEK (ОПТИМИЗИРОВАНЫ ДЛЯ CACHE HIT) =============
# System prompts вынесены в константы для максимального кэширования
# Эти промпты будут кэшироваться при каждом запросе, экономя до 90% стоимости

SYSTEM_PROMPT_TELEGRAM = """Ты крутой фитнес-эксперт и психолог, который пишет посты для Telegram канала про TABATA, HIIT, интервальные тренировки и фитнес для ДЕВУШЕК. Твой стиль - разговорный, как с лучшей подругой, поддерживающий и мотивирующий.

КРИТИЧЕСКИ ВАЖНО:
- МАКСИМАЛЬНАЯ ДЛИНА: 900 символов (включая эмодзи и пробелы) - для Telegram caption с фото
- ВСЯ программа тренировки/диеты должна поместиться (упражнения, подходы, повторения, советы)
- Стиль: разговорный русский, как с подругой, можно сленг, профессиональные термины из фитнеса
- Без воды: только суть, ёмко, по делу, интересно
- Мотивируй: добавь энергии, поддержки, иногда шутки, но строго по делу
- Адаптация: для русского менталитета, понятные примеры
- ЖЕНСКИЕ "БОЛИ": деликатно закрывай их (недостаток времени, сложность начать, страх не справиться, желание похудеть, низкая мотивация) - но с хорошим настроением и поддержкой"""

SYSTEM_PROMPT_ARTICLE = """Ты крутой фитнес-эксперт и копирайтер, который пишет полноценные статьи для блога о фитнесе, здоровье и тренировках для ДЕВУШЕК. Твой стиль - разговорный, но информативный, как с опытным тренером.

КРИТИЧЕСКИ ВАЖНО:
- ДЛИНА: 2000-4000 символов - полноценная статья для сайта
- Стиль: разговорный русский, но с профессиональными терминами
- Структура: введение, основная часть с деталями, практические советы, заключение
- Адаптация: для русского менталитета, понятные примеры
- Без воды: только полезная информация, но развернуто
- Мотивируй: добавь энергии, но профессионально
- ЖЕНСКИЕ "БОЛИ": деликатно закрывай их (недостаток времени, сложность начать, страх не справиться, желание похудеть, низкая мотивация) - но с хорошим настроением и поддержкой"""

# Шаблоны для user prompts (повторяющаяся часть будет кэшироваться)
USER_TEMPLATE_TELEGRAM = """Перепиши эту статью для Telegram поста для ДЕВУШЕК (МАКСИМУМ 900 символов!):

ЗАГОЛОВОК: {заголовок}

ТЕКСТ:
{текст}

ТРЕБОВАНИЯ:
1. Полностью перепиши своими словами, убери ВСЕ следы источника
2. ВСЯ программа тренировки/диеты должна поместиться (упражнения, подходы, повторения, советы)
3. Разговорный стиль: как с лучшей подругой, можно сленг, профессиональные термины
4. Без воды: только суть, ёмко, интересно
5. Мотивируй и поддерживай: энергия, поддержка, иногда шутки, но по делу
6. ДЕЛИКАТНО закрывай женские "боли":
   - "Нет времени" → покажи, что тренировка короткая и эффективная
   - "Сложно начать" → мотивируй, что это проще чем кажется
   - "Страх не справиться" → поддержка, что всё получится
   - "Хочу похудеть" → покажи результат и мотивацию
   - "Низкая мотивация" → вдохновляй, но с хорошим настроением
7. В конце обязательно: как использовать таймер tabatatimer.ru (TABATA/EMOM/HIIT/AMRAP) для этой программы
8. Эмодзи: умеренно, для структуры
9. МАКСИМУМ 900 СИМВОЛОВ! Но ВСЯ программа должна быть!

ПРИМЕР СВЯЗИ С ТАЙМЕРОМ:
"💪 Для этой программы используй режим EMOM на tabatatimer.ru - каждую минуту новое упражнение!"
или
"🔥 Запусти TABATA таймер на tabatatimer.ru и делай каждое упражнение 20 сек, отдых 10 сек!"

ПОМНИ: Максимум 900 символов, но ВСЯ программа должна быть! Пиши для девушек, поддерживай, мотивируй!"""

USER_TEMPLATE_ARTICLE = """Расширь и перепиши эту статью для полноценной статьи на сайте для ДЕВУШЕК (2000-4000 символов):

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
6. Мотивируй и поддерживай: энергия, поддержка, но профессионально
7. ДЕЛИКАТНО закрывай женские "боли":
   - "Нет времени" → покажи, что тренировка короткая и эффективная
   - "Сложно начать" → мотивируй, что это проще чем кажется
   - "Страх не справиться" → поддержка, что всё получится
   - "Хочу похудеть" → покажи результат и мотивацию
   - "Низкая мотивация" → вдохновляй, но с хорошим настроением
8. В конце обязательно: как использовать таймер tabatatimer.ru (TABATA/EMOM/HIIT/AMRAP) для этой программы
9. Эмодзи: умеренно, для структуры
10. ДЛИНА: 2000-4000 символов - полноценная статья!

ПРИМЕР СВЯЗИ С ТАЙМЕРОМ:
"🔥 Для этой программы используй режим EMOM на tabatatimer.ru - каждую минуту новое упражнение из списка по кругу. Всего 5 раундов! Таймер — твой главный тренер здесь."

ПОМНИ: Это полноценная статья для сайта, не короткий пост! Расширь контент, добавь деталей, но сохрани разговорный стиль! Пиши для девушек, поддерживай, мотивируй!"""

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
    """Парсит RSS фид и возвращает список статей (поддерживает RSS 2.0, Atom, FeedBurner)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(rss_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Парсим XML
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError:
            # Пробуем исправить возможные проблемы с кодировкой
            content = response.content.decode('utf-8', errors='ignore')
            root = ET.fromstring(content)
        
        articles = []
        
        # Поддерживаем разные форматы RSS (RSS 2.0, Atom, FeedBurner)
        # Пробуем разные селекторы для поиска элементов
        items = []
        if root.tag == 'rss' or root.tag.endswith('rss'):
            # RSS 2.0
            channel = root.find('channel')
            if channel is not None:
                items = channel.findall('item')
        elif root.tag.endswith('feed') or '{http://www.w3.org/2005/Atom}feed' in root.tag:
            # Atom
            items = root.findall('{http://www.w3.org/2005/Atom}entry')
        
        # Если не нашли, пробуем универсальный поиск
        if not items:
            items = root.findall('.//item') or root.findall('.//entry') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
        
        for item in items:
            try:
                title = ''
                link = ''
                
                # RSS 2.0 формат - ищем прямые дочерние элементы
                title_elem = None
                link_elem = None
                
                # Пробуем разные варианты поиска title
                for child in item:
                    if child.tag == 'title' or child.tag.endswith('}title'):
                        title_elem = child
                        break
                
                # Если не нашли, пробуем через find
                if title_elem is None:
                    title_elem = item.find('title') or item.find('.//title') or item.find('{http://www.w3.org/2005/Atom}title')
                
                # Пробуем разные варианты поиска link
                for child in item:
                    if child.tag == 'link' or child.tag.endswith('}link'):
                        link_elem = child
                        break
                
                # Если не нашли, пробуем через find
                if link_elem is None:
                    link_elem = item.find('link') or item.find('.//link') or item.find('{http://www.w3.org/2005/Atom}link')
                
                # Извлекаем title
                if title_elem is not None:
                    if hasattr(title_elem, 'text') and title_elem.text:
                        title = title_elem.text.strip()
                    elif hasattr(title_elem, 'tail') and title_elem.tail:
                        title = title_elem.tail.strip()
                
                # Извлекаем link (для Atom может быть в атрибуте href, для RSS в text)
                if link_elem is not None:
                    # Сначала пробуем атрибут href (Atom формат)
                    if hasattr(link_elem, 'get') and link_elem.get('href'):
                        link = link_elem.get('href').strip()
                    # Затем пробуем text (RSS 2.0 формат)
                    elif hasattr(link_elem, 'text') and link_elem.text:
                        link = link_elem.text.strip()
                    # Если все еще нет, пробуем найти через guid (RSS 2.0)
                    if not link:
                        guid_elem = item.find('guid')
                        if guid_elem is not None:
                            if hasattr(guid_elem, 'text') and guid_elem.text:
                                link = guid_elem.text.strip()
                            elif hasattr(guid_elem, 'get') and guid_elem.get('isPermaLink') == 'true':
                                link = guid_elem.text.strip() if guid_elem.text else ''
                
                # Публикация дата
                pub_date = None
                for pub_tag in ['pubDate', 'published', '{http://www.w3.org/2005/Atom}published']:
                    pub_elem = item.find(pub_tag)
                    if pub_elem is not None and hasattr(pub_elem, 'text') and pub_elem.text:
                        pub_date = pub_elem.text
                        break
                
                # Описание
                description = ''
                for desc_tag in ['description', '{http://www.w3.org/2005/Atom}summary', 'content', '{http://www.w3.org/2005/Atom}content']:
                    desc_elem = item.find(desc_tag)
                    if desc_elem is not None:
                        if hasattr(desc_elem, 'text') and desc_elem.text:
                            description = desc_elem.text.strip()
                            break
                
                # Добавляем статью только если есть и title и link
                if link and title:
                    articles.append({
                        'title': title,
                        'link': link,
                        'pub_date': pub_date,
                        'description': description
                    })
            except Exception as e:
                # Тихо пропускаем ошибки парсинга отдельных элементов
                continue
        
        if articles:
            print(f"✅ Получено {len(articles)} статей из {rss_url[:60]}...")
        elif len(items) > 0:
            print(f"⚠️ Найдено {len(items)} элементов, но не удалось извлечь статьи из {rss_url[:60]}...")
        return articles
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса RSS {rss_url}: {e}")
        return []
    except Exception as e:
        print(f"❌ Ошибка парсинга RSS {rss_url}: {e}")
        return []

def проверить_релевантность(статья):
    """Проверяет, релевантна ли статья по ключевым словам"""
    текст_для_проверки = (статья.get('title', '') + ' ' + статья.get('description', '')).lower()
    
    найденные_ключевые_слова = []
    for ключевое_слово in RELEVANT_KEYWORDS:
        if ключевое_слово.lower() in текст_для_проверки:
            найденные_ключевые_слова.append(ключевое_слово)
    
    # Считаем релевантной, если найдено хотя бы одно ключевое слово
    релевантна = len(найденные_ключевые_слова) > 0
    
    return релевантна, найденные_ключевые_слова

def парсить_статью(url):
    """Парсит полный текст статьи и изображения с сайта"""
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
                parsed = urlparse(url)
                img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
            elif not img_url.startswith('http'):
                img_url = urljoin(url, img_url)
            
            # Создаём объект изображения для главного
            images.append({
                'url': img_url,
                'alt': '',
                'title': '',
                'is_main': True
            })
        
        # Ищем изображения в статье
        article_images = soup.select('article img, .article-content img, .article-body img, main img, [class*="image"] img, [class*="photo"] img')
        for img in article_images[:20]:  # Увеличиваем до 20 изображений
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
            if not src:
                continue
            
            # Преобразуем относительные URL в абсолютные
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                parsed = urlparse(url)
                src = f"{parsed.scheme}://{parsed.netloc}{src}"
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
            if not any(src.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
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
        
        # Удаляем дубликаты по URL
        unique_images = []
        seen_urls = set()
        for img_dict in images:
            normalized = img_dict['url'].split('?')[0]
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                unique_images.append(img_dict)
        
        images = unique_images[:10]  # Оставляем до 10 релевантных изображений
        
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
    """Делает качественный рерайтинг текста через DeepSeek AI для женской аудитории"""
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
    """Форматирует рерайт для публикации в Telegram с ссылкой на полную статью
    
    Args:
        рерайт: текст поста для Telegram
        оригинальный_заголовок: заголовок статьи (может быть русским)
        post_id: ID поста (для создания slug, если url не передан)
        url: готовый URL статьи (если есть, используется вместо создания slug)
    """
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

def определить_теги(текст, заголовок, источник='womenshealth'):
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
        'твой кишечник', 'твой жкт', 'твой пресс',  # Мужское обращение
        'набор массы', 'набираем массу', 'набрать массу', 'набор мышечной',  # Мужские цели
        'силовая тренировка', 'силовые тренировки', 'силовая',  # Силовые тренировки
        'простата', 'мужское здоровье', 'мужской жкт',  # Мужское здоровье
        'тестостерон',  # Мужские гормоны
        'для мужчин', 'мужчина',  # Явные указания
    ]
    
    if any(маркер in текст_нижний for маркер in мужские_маркеры):
        мужская_аудитория = True
    
    # Контекстные признаки женской аудитории
    женские_маркеры = [
        'подруга', 'девочки', 'дорогие девушки',  # Обращение
        'стройное тело', 'похудеть', 'для девушек', 'для женщин',  # Женские цели
        'женское здоровье', 'женский', 'для девушек',  # Женское здоровье
        'девушкам', 'девушка', 'женщин',  # Явные указания
        '30 дней', 'стройность', 'подтянут', 'тонкое',  # Женские цели
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
    
    if any(word in заголовок_нижний for word in ['девушк', 'женщин', 'для девушек', 'женск', 'женщин']):
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
        'питание девушкам', 'для девушек питание', 'женское питание',
        'до тренировки', 'после тренировки', 'правильное питание'
    ]
    
    if any(маркер in текст_нижний for маркер in питание_маркеры):
        теги.append('Питание')
    
    # ============= ДИЕТЫ =============
    диеты_маркеры = [
        'диет', 'похуден', 'калори', 'дефицит калори', 'профицит',
        'кето', 'палео', 'вегетариан', 'веган', 'средиземноморск',
        'потеря веса', 'сброс веса', 'снижение веса',
        'бжу', 'баланс', 'макрос', 'микрос',
        'диета девушкам', 'для девушек диета', 'женская диета',
        'похудение', 'стройность', 'здоровое питание'
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
        'мотивация девушкам', 'для девушек мотивация', 'женская мотивация',
        'вдохновение', 'сила воли', 'преодоление'
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
        'упражнения девушкам', 'тренировки девушкам', 'для девушек тренировка',
        'стройное тело', 'похудение', '30 дней', 'вызов'
    ]
    
    if any(маркер in текст_нижний for маркер in тренировка_маркеры):
        теги.append('Тренировка')
    
    # ============= СИЛОВЫЕ ТРЕНИРОВКИ =============
    силовые_маркеры = [
        'силовые тренировки', 'силовой тренинг', 'силовая подготовка',
        'weight training', 'strength training', 'силовые',
        'жим лёжа', 'присед со штангой', 'становая тяга',
        'barbell', 'штанга', 'гантели', 'dumbbell',
        'силовой тренинг', 'силовая работа', 'работа с весом',
        'силовые для девушек', 'силовая тренировка для женщин',
        'weight training для девушек', 'сила для девушек'
    ]
    
    if any(маркер in текст_нижний for маркер in силовые_маркеры):
        теги.append('Силовые')
    
    # ============= ФУНКЦИОНАЛЬНЫЙ ТРЕНИНГ =============
    функциональный_маркеры = [
        'функциональный тренинг', 'functional training',
        'функциональные движения', 'functional movement',
        'функционалка', 'functional', 'двигательные паттерны',
        'movement patterns', 'функциональная подготовка',
        'functional fitness', 'функциональный фитнес',
        'функциональный тренинг для девушек', 'functional для женщин'
    ]
    
    if any(маркер in текст_нижний for маркер in функциональный_маркеры):
        теги.append('Функциональный тренинг')
    
    # Если тегов нет, добавляем по умолчанию
    if not теги:
        теги.append('Мотивация')
    
    return теги

def сохранить_пост_в_блог(текст, изображение_url, заголовок, источник='womenshealth', расширенный_текст=None, все_изображения=None, post_id=None):
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
        
        # Проверяем полную уникальность (с учётом заголовка для обнаружения дубликатов)
        уникален, причина = проверить_полную_уникальность(текст, изображение_url, существующие_посты, заголовок)
        
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
        
        # Если DeepSeek не выбрал изображение, используем первое уникальное
        if not лучшее_изображение and все_изображения:
            print("⚠️ DeepSeek не выбрал изображение, ищу первое уникальное...")
            for img_dict in все_изображения:
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
                    лучшее_изображение = img_dict
                    print(f"✅ Найдено уникальное изображение: {img_url[:60]}...")
                    break
        
        # Если все изображения уже используются, берем первое (но это не идеально)
        if not лучшее_изображение and все_изображения:
            print("⚠️ Все изображения уже используются, беру первое из списка")
            лучшее_изображение = все_изображения[0]
        
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
            
            локальное_изображение_url = скачать_и_загрузить_изображение(изображение_для_скачивания, post_id)
            # Если не удалось скачать, используем оригинальный URL
            if not локальное_изображение_url or локальное_изображение_url == изображение_для_скачивания:
                print(f"⚠️ Использую оригинальный URL главного изображения")
                локальное_изображение_url = изображение_для_скачивания
        
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
                локальное_img_url = скачать_и_загрузить_изображение(img_url, img_post_id)
                
                # Если не удалось скачать, используем оригинальный URL
                if not локальное_img_url or локальное_img_url == img_url:
                    локальное_img_url = img_url
                    print(f"  ⚠️ Использую оригинальный URL для изображения {idx + 1}")
                else:
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
    print("🚀 ЗАПУСК ПАРСЕРА WOMEN'S HEALTH")
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
    успешно_обработанных_фидов = 0
    ошибок_фидов = 0
    
    for rss_url in WOMENSHEALTH_RSS_FEEDS:
        # Пропускаем закомментированные фиды
        if rss_url.strip().startswith('#'):
            continue
        
        # Проверяем различные форматы RSS/Atom фидов
        if (rss_url.endswith('.xml') or 
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
                статьи = парсить_rss_feed(rss_url)
                все_статьи.extend(статьи)
                успешно_обработанных_фидов += 1
                if len(статьи) > 0:
                    print(f"✅ {rss_url[:60]}... - получено {len(статьи)} статей")
            except Exception as e:
                ошибок_фидов += 1
                print(f"❌ Ошибка запроса RSS {rss_url}: {e}")
                continue
        else:
            print(f"⏭️ Пропускаем (не RSS формат): {rss_url}")
    
    print(f"\n📊 Статистика парсинга RSS фидов:")
    print(f"   ✅ Успешно обработано фидов: {успешно_обработанных_фидов}")
    print(f"   ❌ Ошибок при парсинге: {ошибок_фидов}")
    
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
    
    for статья in все_статьи:
        if уже_обработана(статья['link']):
            уже_обработанных += 1
            continue
        
        релевантна, ключевые_слова = проверить_релевантность(статья)
        if релевантна:
            релевантные.append(статья)
        else:
            не_релевантных += 1
    
    print(f"✅ Релевантных статей: {len(релевантные)}")
    if уже_обработанных > 0:
        print(f"⚠️ Уже обработано статей: {уже_обработанных}")
    if не_релевантных > 0:
        print(f"⚠️ Не релевантных статей: {не_релевантных}")
    print()
    
    # УЛУЧШЕНИЕ: Выбираем статью с лучшим балансом тематик
    текущий_час_utc = datetime.utcnow().strftime('%H')
    print(f"\n🎯 Выбор статьи с учетом баланса тематик (текущее время: {текущий_час_utc}:00 UTC)...")
    
    # Выбираем статью для баланса из первых 20 релевантных
    выбранная_статья = выбрать_статью_для_баланса(релевантные[:20], текущий_час_utc, n_анализируемых=10)
    
    # Если не удалось выбрать по балансу, используем первую релевантную
    if not выбранная_статья and релевантные:
        print("⚠️ Не удалось выбрать статью по балансу, используем первую релевантную")
        выбранная_статья = релевантные[0]
    
    # Обрабатываем релевантные статьи до тех пор, пока не найдём уникальный контент
    обработано = 0
    максимальное_количество_попыток = min(15, len(релевантные))  # УВЕЛИЧЕНО: Пробуем максимум 15 статей
    
    # Если выбрали статью по балансу, ставим её первой в списке
    статьи_для_обработки = релевантные[:максимальное_количество_попыток]
    if выбранная_статья and выбранная_статья in статьи_для_обработки:
        # Перемещаем выбранную статью в начало списка
        статьи_для_обработки.remove(выбранная_статья)
        статьи_для_обработки.insert(0, выбранная_статья)
        print(f"✅ Приоритет: статья выбрана по балансу тематик")
    
    for i, статья in enumerate(статьи_для_обработки):
        print(f"\n{'='*60}")
        print(f"📝 Попытка {i+1}/{максимальное_количество_попыток}: {статья['title']}")
        print(f"🔗 URL: {статья['link']}")
        ключевые_слова = проверить_релевантность(статья)[1]
        print(f"🔑 Ключевые слова: {', '.join(ключевые_слова[:5])}")
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
        post_id = f"womenshealth_{int(time.time())}"
        
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
        
        # ПРОВЕРКА УНИКАЛЬНОСТИ ПЕРЕД СОХРАНЕНИЕМ
        # Проверяем, нужно ли публиковать на сайт (с HTML страницей)
        публиковать_на_сайт = os.getenv('PUBLISH_TO_BLOG', 'false').lower() == 'true'
        
        if публиковать_на_сайт:
            # ПРОВЕРКА УНИКАЛЬНОСТИ ПЕРЕД СОХРАНЕНИЕМ В БЛОГ
            print("\n🔍 Проверка уникальности перед сохранением в блог...")
            результат_сохранения = сохранить_пост_в_блог(рерайт_telegram, фото_url, статья['title'], 'womenshealth', расширенный_текст, все_изображения, post_id=post_id)
            
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
        успех_telegram = отправить_в_telegram(пост, фото_url)
        
        if успех_telegram:
            сохранить_обработанную_статью(статья['link'])
            обработано += 1
            
            # ЛОГИРОВАНИЕ: Сохраняем информацию о публикации
            теги = определить_теги(рерайт_telegram, заголовок_русский, 'womenshealth')
            аудитория = 'Девушкам' if 'Девушкам' in теги else 'Мужчинам' if 'Мужчинам' in теги else 'Неизвестно'
            
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
                'url': url_статьи if публиковать_на_сайт else None
            })
            
            print("✅ Статья успешно опубликована!\n")
            break  # Успешно обработали, выходим
        else:
            print("❌ Ошибка отправки в Telegram, пробуем следующую...\n")
            # Не сохраняем как обработанную, чтобы попробовать снова позже
        
        # Пауза между статьями
        if i < максимальное_количество_попыток - 1:
            time.sleep(5)
    
    print("=" * 60)
    print(f"✅ Обработано статей: {обработано}")
    print("=" * 60)

if __name__ == '__main__':
    главная()
