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

# ============= КОНФИГУРАЦИЯ =============

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# RSS фиды Women's Health (топовые источники)
WOMENSHEALTH_RSS_FEEDS = [
    'https://www.womenshealthmag.com/rss/all.xml',
    'https://www.shape.com/rss/all.xml',
    'https://www.oxygenmag.com/rss/all.xml',
    'https://www.fitnessmagazine.com/rss/all.xml',
    'https://www.fitbottomedgirls.com/feed/',
    'https://www.girlsgonesstrong.com/feed/',
    'https://www.toneitup.com/blog/feed/',
    'https://www.thefitnessista.com/feed/',
    'https://www.healthywomen.org/feeds/feed.rss',
    'https://www.sheknows.com/health-and-wellness/feed/',
    'https://www.intimina.com/blog/feed',
    'https://www.floliving.com/blog/feed/',
    'https://www.kaiafit.com/blog/feed/',
    'https://www.healthista.com/feed/',
    'https://www.womenfitness.net/feed/'
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
        
        # Поддерживаем разные форматы RSS
        items = root.findall('.//item') or root.findall('.//entry')
        
        for item in items:
            try:
                title_elem = item.find('title') or item.find('.//title')
                link_elem = item.find('link') or item.find('.//link')
                pub_date_elem = item.find('pubDate') or item.find('published') or item.find('.//pubDate')
                
                if title_elem is not None and link_elem is not None:
                    title = title_elem.text or ''
                    link = link_elem.text or link_elem.get('href', '')
                    
                    if link:
                        articles.append({
                            'title': title,
                            'link': link,
                            'pub_date': pub_date_elem.text if pub_date_elem is not None else None
                        })
            except Exception as e:
                continue
        
        print(f"✅ Получено {len(articles)} статей из {rss_url}")
        return articles
    
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
        if rss_url.endswith('.xml') or rss_url.endswith('/feed') or rss_url.endswith('/feed/'):
            статьи = парсить_rss_feed(rss_url)
            все_статьи.extend(статьи)
        else:
            print(f"⏭️ Пропускаем: {rss_url}")
    
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
    
    # Обрабатываем релевантные статьи (максимум 2 за запуск)
    обработано = 0
    for статья in релевантные[:2]:
        if обработано >= 2:
            break
        
        print(f"📝 Обрабатываем статью: {статья['title']}")
        print(f"🔗 URL: {статья['link']}")
        ключевые_слова = проверить_релевантность(статья)[1]
        print(f"🔑 Ключевые слова: {', '.join(ключевые_слова[:5])}")
        print()
        
        # Парсим полный текст
        print("📥 Парсинг статьи...")
        полный_текст = парсить_статью(статья['link'])
        
        if not полный_текст:
            print("⚠️ Не удалось получить текст статьи, пропускаем\n")
            continue
        
        print(f"✅ Получен контент ({len(полный_текст)} символов)")
        
        # Ищем изображения
        изображения = найти_изображения(статья['link'])
        print(f"✅ Найдено изображений: {len(изображения)}")
        print()
        
        # Рерайтинг через DeepSeek
        print("🤖 Рерайтинг через DeepSeek AI...")
        рерайт = рерайтить_через_deepseek(полный_текст, статья['title'])
        
        if not рерайт:
            print("⚠️ Не удалось сделать рерайтинг, пропускаем\n")
            continue
        
        print()
        
        # Форматируем пост
        пост = форматировать_пост(рерайт, статья['title'])
        
        # Отправляем в Telegram
        print("📤 Отправка в Telegram...")
        фото_url = изображения[0] if изображения else None
        успех = отправить_в_telegram(пост, фото_url)
        
        if успех:
            сохранить_обработанную_статью(статья['link'])
            обработано += 1
            print("✅ Статья успешно опубликована!\n")
        else:
            print("❌ Ошибка публикации статьи\n")
        
        # Пауза между статьями
        if обработано < len(релевантные[:2]):
            time.sleep(5)
    
    print("=" * 60)
    print(f"✅ Обработано статей: {обработано}")
    print("=" * 60)

if __name__ == '__main__':
    главная()
