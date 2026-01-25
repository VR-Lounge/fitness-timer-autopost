#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления заголовков уже опубликованных статей
Использует оригинальные заголовки из source_url и создаёт заголовки на основе контента
"""

import json
import sys
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import re

# Добавляем путь к модулям
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

from create_title_from_content import создать_заголовок_на_основе_контента

# Определяем пути
if (SCRIPT_DIR.parent / 'public_html').exists():
    REPO_ROOT = SCRIPT_DIR.parent
elif (SCRIPT_DIR / 'public_html').exists():
    REPO_ROOT = SCRIPT_DIR
else:
    REPO_ROOT = Path.cwd()

BLOG_POSTS_FILE = REPO_ROOT / 'public_html' / 'blog-posts.json'

def получить_оригинальный_заголовок(url):
    """Получает оригинальный заголовок статьи из source_url"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Для skinnyms.com
        if 'skinnyms.com' in url:
            title_el = soup.select_one("h1.entry-title, h1.post-title, h1")
            if title_el:
                return title_el.get_text(strip=True)
        
        # Для других источников
        selectors = [
            'h1.entry-title',
            'h1.post-title',
            'h1.article-title',
            'article h1',
            'h1',
            'meta[property="og:title"]'
        ]
        
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                if selector.startswith('meta'):
                    return el.get('content', '').strip()
                else:
                    return el.get_text(strip=True)
        
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        return None
    except Exception as e:
        print(f"⚠️ Ошибка получения заголовка из {url}: {e}")
        return None

def обновить_заголовки_статей():
    """Обновляет заголовки проблемных статей"""
    # Скачиваем актуальный файл с сайта
    print("📥 Скачиваю blog-posts.json с сайта...")
    try:
        response = requests.get("https://www.tabatatimer.ru/blog-posts.json", timeout=30)
        response.raise_for_status()
        data = json.loads(response.text)
    except Exception as e:
        print(f"❌ Ошибка скачивания файла: {e}")
        # Пробуем использовать локальный файл
        if BLOG_POSTS_FILE.exists():
            print("📂 Использую локальный файл...")
            with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            print("❌ Нет доступа к файлу")
            return
    
    posts = data.get('posts', [])
    print(f"📊 Всего постов: {len(posts)}")
    
    # Проблемные статьи
    problem_slugs = [
        'muzhskoy-zhkt-chto-nuzhno-znat-i-kak-zaschitit-kis',
        'gotov-k-lyubomu-vyzovu-programma-trenirovok',
        'poleznaya-statya-o-fitnese-i-zdorove'
    ]
    
    исправлено = 0
    for post in posts:
        url = post.get('url', '')
        if not url:
            continue
        
        # Проверяем, является ли это проблемной статьёй
        current_title = post.get('title', '').lower()
        is_problem = (
            any(slug in url for slug in problem_slugs) or
            'мужской жкт' in current_title or
            'готов к любому вызову' in current_title or
            'полезная статья о фитнесе' in current_title
        )
        if not is_problem:
            continue
        
        source_url = post.get('source_url', '')
        if not source_url:
            print(f"⚠️ Нет source_url для {url}")
            continue
        
        print(f"\n🔍 Обрабатываю: {url}")
        print(f"   Source URL: {source_url}")
        print(f"   Текущий заголовок: {post.get('title', 'N/A')}")
        
        # Получаем оригинальный заголовок
        оригинальный_заголовок = получить_оригинальный_заголовок(source_url)
        
        if not оригинальный_заголовок:
            print(f"   ❌ Не удалось получить оригинальный заголовок")
            continue
        
        # Очищаем от технических признаков
        оригинальный_заголовок = re.sub(r'podcast\s*#?\s*\d+[,:]?\s*', '', оригинальный_заголовок, flags=re.IGNORECASE)
        оригинальный_заголовок = re.sub(r'episode\s*#?\s*\d+[,:]?\s*', '', оригинальный_заголовок, flags=re.IGNORECASE)
        оригинальный_заголовок = re.sub(r'#\s*\d+[,:]?\s*', '', оригинальный_заголовок)
        оригинальный_заголовок = оригинальный_заголовок.strip(' -—:')
        
        print(f"   ✅ Оригинальный заголовок: {оригинальный_заголовок}")
        
        # Создаём заголовок на основе контента
        контент = post.get('text', '')
        if not контент:
            print(f"   ⚠️ Нет контента, используем оригинальный заголовок")
            новый_заголовок = оригинальный_заголовок
        else:
            print(f"   🤖 Создаю заголовок на основе контента через DeepSeek...")
            новый_заголовок = создать_заголовок_на_основе_контента(контент, оригинальный_заголовок)
            print(f"   ✅ Новый заголовок: {новый_заголовок}")
        
        post['title'] = новый_заголовок
        исправлено += 1
        print(f"   ✅ Заголовок обновлён!")
    
    if исправлено > 0:
        # Сохраняем обновлённый файл
        with open(BLOG_POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Исправлено заголовков: {исправлено}")
        print(f"📝 Файл сохранён: {BLOG_POSTS_FILE}")
        
        # Перегенерируем HTML страницы
        print(f"\n📄 Перегенерирую HTML страницы...")
        try:
            from generate_blog_post_page import сгенерировать_страницы_для_всех_постов
            сгенерировать_страницы_для_всех_постов()
        except Exception as e:
            print(f"⚠️ Ошибка генерации HTML: {e}")
    else:
        print("\n⚠️ Не найдено статей для исправления")

if __name__ == '__main__':
    обновить_заголовки_статей()
