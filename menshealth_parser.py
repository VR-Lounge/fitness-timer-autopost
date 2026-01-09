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

# ============= КОНФИГУРАЦИЯ =============

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# RSS фиды Men's Health
MENSHEALTH_RSS_FEEDS = [
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
        system_prompt = """Ты профессиональный фитнес-копирайтер, специализирующийся на интервальных тренировках (TABATA, HIIT, AMRAP, EMOM).

Твоя задача - переписать статью о тренировках или питании, сделав её уникальной и адаптированной для русскоязычной аудитории сайта tabatatimer.ru.

ТРЕБОВАНИЯ:
1. Полностью перепиши текст своими словами, сохраняя смысл и полезную информацию
2. Убери все упоминания Men's Health, авторов оригинальной статьи, ссылки на источник
3. Используй разговорный стиль, как будто пишешь для друзей-спортсменов
4. Добавь упоминания о табата таймере, интервальных тренировках, если это уместно
5. Сохрани структуру: введение, основная часть, вывод
6. Используй эмодзи для визуального оформления (но не переборщи)
7. Длина текста: 800-1200 слов
8. Пиши на русском языке
9. Не используй цитаты и ссылки на источники
10. Сделай текст живым и мотивирующим"""
        
        user_prompt = f"""Перепиши эту статью о тренировках/питании для сайта tabatatimer.ru:

ЗАГОЛОВОК: {заголовок}

ТЕКСТ:
{оригинальный_текст[:3000]}

Сделай качественный рерайтинг: полностью перепиши своими словами, убери все следы источника, адаптируй для русскоязычной аудитории, добавь упоминания о табата таймере и интервальных тренировках где уместно."""
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
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
                текст = текст[:1000] + "\n\n... (продолжение на сайте: tabatatimer.ru)"
                print(f"⚠️ Текст обрезан до 1024 символов (было {len(текст)} символов)")
            
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
    # Добавляем хештеги и ссылку на сайт
    пост = f"""{рерайт}

💪 Используй наш табата таймер для интервальных тренировок: https://www.tabatatimer.ru

#Табата #HIIT #Тренировки #Фитнес"""
    
    # Ограничиваем длину для caption с фото (1024 символа)
    # Если текст будет отправляться с фото, он будет обрезан в функции отправить_в_telegram
    # Для текстовых сообщений лимит 4096 символов
    if len(пост) > 4000:
        пост = пост[:3950] + "\n\n... (продолжение на сайте: tabatatimer.ru)"
    
    return пост

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
        if rss_url.endswith('.xml/') or rss_url.endswith('.xml'):
            # Это RSS фид
            статьи = парсить_rss_feed(rss_url)
            все_статьи.extend(статьи)
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
    
    # Обрабатываем первую релевантную статью
    статья = релевантные[0]
    print(f"\n📝 Обрабатываем статью: {статья['title']}")
    print(f"🔗 URL: {статья['link']}")
    print(f"🔑 Ключевые слова: {', '.join(статья['keywords'])}")
    
    # Парсим полный текст и изображения
    print("\n📥 Парсинг статьи...")
    parsed = парсить_статью(статья['link'])
    
    if not parsed or not parsed['content']:
        print("❌ Не удалось получить контент статьи")
        return
    
    print(f"✅ Получен контент ({len(parsed['content'])} символов)")
    print(f"✅ Найдено изображений: {len(parsed['images'])}")
    
    # Рерайтинг через DeepSeek
    print("\n🤖 Рерайтинг через DeepSeek AI...")
    рерайт = рерайтить_через_deepseek(parsed['content'], статья['title'])
    
    if not рерайт:
        print("❌ Не удалось выполнить рерайтинг")
        return
    
    # Форматируем пост
    пост = форматировать_пост(рерайт, статья['title'])
    
    # Выбираем лучшее изображение
    фото_url = parsed['images'][0] if parsed['images'] else None
    
    # Отправляем в Telegram
    print("\n📤 Отправка в Telegram...")
    успех = отправить_в_telegram(пост, фото_url)
    
    if успех:
        # Сохраняем как обработанную
        сохранить_обработанную_статью(статья['link'])
        print(f"\n✅ Статья успешно обработана и опубликована!")
    else:
        print(f"\n❌ Ошибка публикации статьи")

if __name__ == '__main__':
    главная()
