#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Скрипт для восстановления потерянных статей блога
    Добавляет URL к существующим статьям на основе реальных HTML файлов
"""

import json
from pathlib import Path
from datetime import datetime

# Пути к файлам
SCRIPT_DIR = Path(__file__).parent.absolute()
REPO_ROOT = SCRIPT_DIR.parent
PUBLIC_HTML_DIR = REPO_ROOT / 'public_html'
BLOG_POSTS_FILE = PUBLIC_HTML_DIR / 'blog-posts.json'
BLOG_DIR = PUBLIC_HTML_DIR / 'blog'

# Маппинг ID статей на реальные URL из HTML файлов
ID_TO_URL_MAP = {
    'nutrition_1': 'pravilnoe-pitanie-dlya-trenirovok-chto-est-do-i-po.html',
    'mens_workout_1': 'silovaya-trenirovka-dlya-muzhchin-nabiraem-massu-z.html',
    'womens_workout_1': 'trenirovka-dlya-devushek-stroynoe-telo-za-30-dney.html',
    'diet_1': 'sredizemnomorskaya-dieta-nauchno-dokazannyy-put-k-.html',
    'motivation_1': 'nachni-segodnya-pochemu-ne-stoit-otkladyvat-trenir.html',
}

def main():
    """Главная функция восстановления"""
    print("📋 ВОССТАНОВЛЕНИЕ СТАТЕЙ БЛОГА")
    print("=" * 60)
    
    # Загружаем blog-posts.json
    if not BLOG_POSTS_FILE.exists():
        print(f"❌ Файл {BLOG_POSTS_FILE} не найден!")
        return
    
    with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    посты = data.get('posts', [])
    print(f"✅ Загружено статей: {len(посты)}")
    
    # Восстанавливаем URL для старых статей
    обновлено = 0
    for пост in посты:
        post_id = пост.get('id', '')
        
        # Если у статьи нет URL, но есть маппинг
        if 'url' not in пост and post_id in ID_TO_URL_MAP:
            url_slug = ID_TO_URL_MAP[post_id]
            url = f"https://www.tabatatimer.ru/blog/{url_slug}"
            пост['url'] = url
            обновлено += 1
            print(f"✅ Добавлен URL для {post_id}: {url_slug}")
        elif 'url' not in пост:
            # Для новых статей создаём URL на основе ID или заголовка
            import re
            заголовок = пост.get('title', post_id)
            # Создаём slug из заголовка
            slug = заголовок.lower()
            транслит = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
            }
            slug_translit = ''
            for char in slug:
                if char in транслит:
                    slug_translit += транслит[char]
                elif char.isalnum() or char in '- ':
                    slug_translit += char
                else:
                    slug_translit += '-'
            slug = re.sub(r'[-\s]+', '-', slug_translit).strip('-')[:50]
            if not slug:
                slug = post_id.replace('_', '-')
            url = f"https://www.tabatatimer.ru/blog/{slug}.html"
            пост['url'] = url
            обновлено += 1
            print(f"✅ Создан URL для {post_id}: {slug}.html")
    
    if обновлено > 0:
        # Создаём backup
        backup_file = BLOG_POSTS_FILE.with_suffix('.json.backup2')
        if BLOG_POSTS_FILE.exists():
            import shutil
            shutil.copy2(BLOG_POSTS_FILE, backup_file)
            print(f"✅ Создан backup: {backup_file.name}")
        
        # Сохраняем обновлённый файл
        with open(BLOG_POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Обновлено статей: {обновлено}")
        print(f"✅ blog-posts.json сохранён")
    else:
        print("\n⚠️ Не было изменений")
    
    # Выводим финальную статистику
    print(f"\n📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
    print(f"   Всего статей: {len(посты)}")
    статей_с_url = sum(1 for p in посты if 'url' in p)
    print(f"   Статей с URL: {статей_с_url}")
    print(f"   Статей без URL: {len(посты) - статей_с_url}")

if __name__ == '__main__':
    main()
