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

# ============= КОНФИГУРАЦИЯ =============

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# RSS фиды Women's Health (70 источников)
WOMENSHEALTH_RSS_FEEDS = [
    # 1-10
    'https://www.healthywomen.org/feeds/feed.rss',
    'https://www.intimina.com/blog/feed/',
    'https://www.sheknows.com/health-and-wellness/feed/',
    'https://adriaticawomenshealth.com/newsblog/feed/',
    'https://gymbunny.ie/feed/',
    'https://nourishinglab.com/feed/',
    'https://www.fempower-health.com/blog-feed.xml',
    'https://www.fit4females.com/fitblog/feed/',
    'https://www.womenshealthkc.com/resources-forms/blog?format=feed',
    'https://sarahfit.com/feed/',
    # 11-20
    'http://knocked-upfitness.com/feed/',
    'https://bwhi.org/feed/',
    'https://healthworksfitness.com/feed/',
    'https://blogs.womans.org/feed/',
    'https://womensmentalhealth.org/feed/',
    'https://blog.metagenics.com/post/category/womens-health/feed/',
    'https://womensfitnessclubs.com/feed/',
    'https://sanitydaily.com/feed/',
    'https://jessicasepel.com/feed/',
    'http://www.livingbetter50.com/category/health-fitness/feed/',
    # 21-30
    'https://www.healthista.com/feed/',
    'https://www.womenfitness.net/feed/',
    'https://flecksoflex.com/feed/',
    'https://femalefitnesssystems.com/feed/',
    'https://www.fitnessmag.co.za/feed/',
    'https://www.femalle.net/feed/',
    'https://fitnessista.com/feed/',
    'https://blivewear.com/feed/',
    'https://www.kimberleypayne.com/feed/',
    'https://bebodywise.com/blog/rss/',
    # 31-40
    'https://whcsmd.com/feed/',
    'https://lazygirlfitness.com.au/feed/',
    'https://azgyn.com/feed/',
    'https://vivamagonline.com/feed/',
    'https://fitbottomedgirls.com/feed',
    'https://www.girlsgonesstrong.com/feed/',
    'https://theflowerempowered.com/feed/',
    'https://my.toneitup.com/blogs/latest.atom',
    'https://www.innovativewomen.net//feed/rss2',
    'https://kathydolanhealthfitness.blogspot.com/feeds/posts/default?alt=rss',
    # 41-50
    'https://newriverwomenshealth.com/feed/',
    'https://femmephysiques.com/feed/',
    'https://www.stronghealthywoman.com/feed/',
    'https://noomikajsa.com/feed/',
    'http://vgcfitlifestyle.blogspot.com/feeds/posts/default',
    'http://www.heartlandwomenshealth.com/blog?format=RSS',
    'https://www.jerseygirltalk.com/feed/',
    'https://fitness4her.com/feed/',
    'https://thefithabit.com/feed/',
    'https://thehoneypot.co/blogs/latest.atom',
    # 51-60
    'http://fitnessontoast.com/feed/',
    'https://www.vuvatech.com/blogs/care.atom',
    'https://takingthemysteryoutof50.com/feed/',
    'https://www.besthealthmag.ca/wellness/health/feed/',
    'https://www.kaylainthecity.com/feed/',
    'https://womenshealthtoday.blog/feed/',
    'https://niashanks.com/feed/',
    'https://juliabuckleyfitness.com/feed/',
    'https://amodrn.com/feed/',
    'http://www.nwwomensfitness.com/feed/',
    # 61-70
    'https://stayhealthyfitness.blogspot.com/feeds/posts/default?alt=rss',
    'https://www.hormona.io/feed/',
    'https://www.jillbrownfitness.com/feed/',
    'https://www.bepreparedperiod.com/blog/feed/',
    'https://kaldascenter.com/blog?format=rss',
    'http://whepducom.blogspot.com/feeds/posts/default?alt=rss',
    'https://www.drdawnswellnesstools.com/blog-feed.xml',
    # Дополнительные проверенные источники
    'https://www.womenshealthmag.com/rss/all.xml',
    'https://www.shape.com/rss/all.xml',
    'https://www.oxygenmag.com/rss/all.xml',
    'https://www.fitnessmagazine.com/rss/all.xml',
    'https://www.floliving.com/blog/feed/',
    'https://www.kaiafit.com/blog/feed/'
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
        items = root.findall('.//item') or root.findall('.//entry')
        
        for item in items:
            try:
                # RSS 2.0 формат
                title_elem = item.find('title') or item.find('.//title')
                link_elem = item.find('link') or item.find('.//link')
                pub_date_elem = item.find('pubDate') or item.find('published') or item.find('.//pubDate')
                
                # Atom формат
                if not title_elem:
                    title_elem = item.find('{http://www.w3.org/2005/Atom}title')
                if not link_elem:
                    link_elem = item.find('{http://www.w3.org/2005/Atom}link')
                    if link_elem is not None:
                        link = link_elem.get('href', '')
                    else:
                        link = ''
                else:
                    link = link_elem.text or link_elem.get('href', '') if link_elem is not None else ''
                
                if title_elem is not None and link:
                    title = title_elem.text or ''
                    if not link and link_elem is not None:
                        link = link_elem.text or link_elem.get('href', '')
                    
                    if link and title:
                        articles.append({
                            'title': title.strip(),
                            'link': link.strip(),
                            'pub_date': pub_date_elem.text if pub_date_elem is not None else None,
                            'description': (item.find('description') or item.find('{http://www.w3.org/2005/Atom}summary') or item.find('.//description')).text if (item.find('description') or item.find('{http://www.w3.org/2005/Atom}summary') or item.find('.//description')) is not None else ''
                        })
            except Exception as e:
                continue
        
        if articles:
            print(f"✅ Получено {len(articles)} статей из {rss_url}")
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
    """Парсит полный текст статьи с сайта"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Удаляем ненужные элементы
        for script in soup(["script", "style", "nav", "footer", "aside", "header"]):
            script.decompose()
        
        # Ищем основной контент
        article_content = soup.find('article') or soup.find('main') or soup.find('div', class_=re.compile('content|article|post'))
        
        if article_content:
            # Извлекаем текст
            paragraphs = article_content.find_all(['p', 'h1', 'h2', 'h3', 'h4'])
            текст = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            # Ограничиваем размер
            if len(текст) > 5000:
                текст = текст[:5000]
            
            return текст
        else:
            # Если не нашли article, берём весь body
            body = soup.find('body')
            if body:
                текст = body.get_text(separator='\n\n', strip=True)
                if len(текст) > 5000:
                    текст = текст[:5000]
                return текст
        
        return None
    
    except Exception as e:
        print(f"❌ Ошибка парсинга статьи {url}: {e}")
        return None

def найти_изображения(url):
    """Находит изображения в статье"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        изображения = []
        
        # Ищем og:image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image.get('content')
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                parsed = urlparse(url)
                img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
            изображения.append(img_url)
        
        # Ищем изображения в статье
        article_content = soup.find('article') or soup.find('main') or soup.find('div', class_=re.compile('content|article|post'))
        if article_content:
            for img in article_content.find_all('img', src=True):
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        parsed = urlparse(url)
                        img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
                    
                    # Проверяем размер (пропускаем маленькие иконки)
                    try:
                        width = img.get('width') or img.get('data-width')
                        height = img.get('height') or img.get('data-height')
                        if width and height:
                            try:
                                if int(width) < 200 or int(height) < 200:
                                    continue  # Пропускаем маленькие изображения
                            except (ValueError, TypeError):
                                pass
                    except Exception:
                        pass
                    
                    if img_url not in изображения:
                        изображения.append(img_url)
        
        return изображения[:3]  # Возвращаем до 3 изображений
    
    except Exception as e:
        print(f"❌ Ошибка поиска изображений {url}: {e}")
        return []

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
        
        # Промпт для рерайтинга для женской аудитории
        system_prompt = """Ты крутой фитнес-эксперт и психолог, который пишет посты для Telegram канала про TABATA, HIIT, интервальные тренировки и фитнес для ДЕВУШЕК. Твой стиль - разговорный, как с лучшей подругой, поддерживающий и мотивирующий.

КРИТИЧЕСКИ ВАЖНО:
- МАКСИМАЛЬНАЯ ДЛИНА: 900 символов (включая эмодзи и пробелы) - для Telegram caption с фото
- ВСЯ программа тренировки/диеты должна поместиться (упражнения, подходы, повторения, советы)
- Стиль: разговорный русский, как с подругой, можно сленг, профессиональные термины из фитнеса
- Без воды: только суть, ёмко, по делу, интересно
- Мотивируй: добавь энергии, поддержки, иногда шутки, но строго по делу
- Адаптация: для русского менталитета, понятные примеры
- ЖЕНСКИЕ "БОЛИ": деликатно закрывай их (недостаток времени, сложность начать, страх не справиться, желание похудеть, низкая мотивация) - но с хорошим настроением и поддержкой"""
        
        user_prompt = f"""Перепиши эту статью для Telegram поста для ДЕВУШЕК (МАКСИМУМ 900 символов!):

ЗАГОЛОВОК: {заголовок}

ТЕКСТ:
{оригинальный_текст[:4000]}

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
    
    # Девушкам
    if any(word in текст_нижний for word in ['девушк', 'женщин', 'для девочек', 'девушкам', 'женский']):
        теги.append('Девушкам')
    
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

def сохранить_пост_в_блог(текст, изображение_url, заголовок, источник='womenshealth'):
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
        
        # Создаём новый пост
        новый_пост = {
            'id': f"{источник}_{int(time.time())}",
            'title': заголовок,
            'text': текст,
            'image': изображение_url,
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
    for rss_url in WOMENSHEALTH_RSS_FEEDS:
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
            except Exception as e:
                print(f"⚠️ Ошибка парсинга {rss_url}: {e}")
                continue
        else:
            print(f"⏭️ Пропускаем (не RSS формат): {rss_url}")
    
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
            релевантные.append(статья)
    
    print(f"✅ Релевантных статей: {len(релевантные)}\n")
    
    # Обрабатываем релевантные статьи до тех пор, пока не найдём уникальный контент
    обработано = 0
    максимальное_количество_попыток = min(5, len(релевантные))  # Пробуем максимум 5 статей
    
    for i, статья in enumerate(релевантные[:максимальное_количество_попыток]):
        print(f"\n{'='*60}")
        print(f"📝 Попытка {i+1}/{максимальное_количество_попыток}: {статья['title']}")
        print(f"🔗 URL: {статья['link']}")
        ключевые_слова = проверить_релевантность(статья)[1]
        print(f"🔑 Ключевые слова: {', '.join(ключевые_слова[:5])}")
        print(f"{'='*60}\n")
        
        # Парсим полный текст
        print("📥 Парсинг статьи...")
        полный_текст = парсить_статью(статья['link'])
        
        if not полный_текст:
            print("⚠️ Не удалось получить текст статьи, пробуем следующую...\n")
            continue
        
        print(f"✅ Получен контент ({len(полный_текст)} символов)")
        
        # Ищем изображения
        изображения = найти_изображения(статья['link'])
        print(f"✅ Найдено изображений: {len(изображения)}")
        
        if not изображения:
            print("⚠️ Нет изображений, пробуем следующую статью...\n")
            continue
        
        print()
        
        # Рерайтинг через DeepSeek
        print("🤖 Рерайтинг через DeepSeek AI...")
        рерайт = рерайтить_через_deepseek(полный_текст, статья['title'])
        
        if not рерайт:
            print("⚠️ Не удалось сделать рерайтинг, пробуем следующую...\n")
            continue
        
        print()
        
        # Форматируем пост
        пост = форматировать_пост(рерайт, статья['title'])
        
        # Выбираем лучшее изображение
        фото_url = изображения[0]
        
        # ПРОВЕРКА УНИКАЛЬНОСТИ ПЕРЕД СОХРАНЕНИЕМ
        print("\n🔍 Проверка уникальности перед сохранением...")
        успех_сохранения = сохранить_пост_в_блог(пост, фото_url, статья['title'], 'womenshealth')
        
        if not успех_сохранения:
            print("⚠️ Контент не уникален, пробуем следующую статью...\n")
            # Сохраняем как обработанную, чтобы не пытаться снова
            сохранить_обработанную_статью(статья['link'])
            continue
        
        # Если контент уникален и сохранён, отправляем в Telegram
        print("\n📤 Отправка в Telegram...")
        успех_telegram = отправить_в_telegram(пост, фото_url)
        
        if успех_telegram:
            сохранить_обработанную_статью(статья['link'])
            обработано += 1
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
