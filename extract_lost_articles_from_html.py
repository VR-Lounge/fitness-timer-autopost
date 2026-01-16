#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Скрипт для извлечения данных из существующих HTML файлов потерянных статей
    и восстановления их в blog-posts.json
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import unquote

# Пути к файлам
SCRIPT_DIR = Path(__file__).parent.absolute()
REPO_ROOT = SCRIPT_DIR.parent
PUBLIC_HTML_DIR = REPO_ROOT / 'public_html'
BLOG_POSTS_FILE = PUBLIC_HTML_DIR / 'blog-posts.json'
BLOG_DIR = PUBLIC_HTML_DIR / 'blog'

def извлечь_данные_из_html(html_file):
    """Извлекает данные статьи из HTML файла"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Извлекаем заголовок
        h1 = soup.find('h1', class_='blog-post-title')
        title = h1.text.strip() if h1 else 'Без названия'
        
        # Извлекаем дату
        meta_date = soup.find('meta', property='article:published_time')
        date_str = meta_date.get('content', '') if meta_date else ''
        
        # Извлекаем теги
        tags_meta = soup.find_all('meta', property='article:tag')
        tags = [tag.get('content', '') for tag in tags_meta if tag.get('content')]
        
        # Извлекаем изображение
        img = soup.find('img', class_='blog-post-image')
        image_url = img.get('src', '') if img else ''
        
        # Извлекаем текст статьи
        content_div = soup.find('div', class_='blog-post-content')
        if content_div:
            # Убираем блок с таймером
            timer_block = content_div.find('div', class_='blog-timer-block')
            if timer_block:
                timer_block.decompose()
            
            # Получаем текст с сохранением структуры
            # Конвертируем HTML обратно в текст, сохраняя форматирование
            text_parts = []
            for element in content_div.children:
                if hasattr(element, 'name'):
                    if element.name == 'p':
                        text_parts.append(element.get_text().strip())
                    elif element.name in ['h3', 'h4']:
                        text_parts.append(f"**{element.get_text().strip()}**")
                    elif element.name == 'ol':
                        for li in element.find_all('li', recursive=False):
                            text_parts.append(f"- {li.get_text().strip()}")
                    elif element.name == 'ul':
                        for li in element.find_all('li', recursive=False):
                            text_parts.append(f"- {li.get_text().strip()}")
                    elif element.get_text().strip():
                        text_parts.append(element.get_text().strip())
                elif str(element).strip():
                    text_parts.append(str(element).strip())
            
            text = '\n\n'.join(filter(None, text_parts))
            # Убираем лишние переносы строк
            text = re.sub(r'\n{3,}', '\n\n', text)
        else:
            text = ''
        
        return {
            'title': title,
            'text': text,
            'image': image_url,
            'tags': tags,
            'date': date_str,
            'filename': html_file.name
        }
    except Exception as e:
        print(f"❌ Ошибка при извлечении данных из {html_file.name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def создать_id_из_filename(filename):
    """Создаёт ID из имени файла или использует известные маппинги"""
    # Известные маппинги slug -> id
    slug_to_id = {
        'pravilnoe-pitanie-dlya-trenirovok-chto-est-do-i-po.html': 'nutrition_1',
        'silovaya-trenirovka-dlya-muzhchin-nabiraem-massu-z.html': 'mens_workout_1',
        'trenirovka-dlya-devushek-stroynoe-telo-za-30-dney.html': 'womens_workout_1',
        'sredizemnomorskaya-dieta-nauchno-dokazannyy-put-k-.html': 'diet_1',
        'nachni-segodnya-pochemu-ne-stoit-otkladyvat-trenir.html': 'motivation_1',
    }
    
    if filename in slug_to_id:
        return slug_to_id[filename]
    
    # Для новых файлов создаём ID из имени
    base = filename.replace('.html', '').replace('-', '_')
    parts = base.split('_')[:3]
    post_id = '_'.join(parts)
    return post_id

def main():
    """Главная функция"""
    print("📋 ВОССТАНОВЛЕНИЕ ПОТЕРЯННЫХ СТАТЕЙ БЛОГА ИЗ HTML ФАЙЛОВ")
    print("=" * 60)
    
    # Проверяем наличие директории blog/
    if not BLOG_DIR.exists():
        print(f"❌ Директория {BLOG_DIR} не найдена!")
        return
    
    # Загружаем текущий blog-posts.json
    if BLOG_POSTS_FILE.exists():
        with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            existing_posts = {post['id'] for post in data.get('posts', [])}
            existing_urls = {post.get('url', '') for post in data.get('posts', []) if 'url' in post}
    else:
        data = {'posts': []}
        existing_posts = set()
        existing_urls = set()
    
    print(f"✅ Загружен blog-posts.json: {len(data['posts'])} статей")
    print(f"✅ Существующие ID: {', '.join(existing_posts)}")
    
    # Находим все HTML файлы в blog/
    html_files = list(BLOG_DIR.glob('*.html'))
    print(f"\n📁 Найдено HTML файлов: {len(html_files)}")
    
    # Извлекаем данные из всех HTML файлов
    restored_posts = []
    processed_files = []
    
    for html_file in sorted(html_files):
        filename = html_file.name
        print(f"\n📄 Обрабатываю: {filename}")
        
        article_data = извлечь_данные_из_html(html_file)
        
        if not article_data:
            print(f"⚠️ Не удалось извлечь данные из {filename}")
            continue
        
        # Создаём ID
        post_id = создать_id_из_filename(filename)
        
        # Проверяем, нет ли уже такой статьи
        if post_id in existing_posts:
            print(f"⚠️ Статья с ID {post_id} уже есть в blog-posts.json, пропускаю...")
            processed_files.append(filename)
            continue
        
        # Создаём URL из имени файла
        url_slug = filename.replace('.html', '')
        post_url = f"https://www.tabatatimer.ru/blog/{filename}"
        
        # Парсим дату
        try:
            if article_data['date']:
                if 'T' in article_data['date']:
                    date_obj = datetime.fromisoformat(article_data['date'].replace('Z', '+00:00'))
                else:
                    date_obj = datetime.strptime(article_data['date'], '%Y-%m-%d')
                timestamp = int(date_obj.timestamp())
                date_iso = date_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                # Используем дату создания файла
                timestamp = int(html_file.stat().st_mtime)
                date_obj = datetime.fromtimestamp(timestamp)
                date_iso = date_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        except Exception as e:
            print(f"⚠️ Ошибка парсинга даты: {e}, использую текущую дату")
            date_obj = datetime.now()
            timestamp = int(date_obj.timestamp())
            date_iso = date_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Создаём объект поста
        post = {
            'id': post_id,
            'title': article_data['title'],
            'text': article_data['text'],
            'image': article_data['image'],
            'tags': article_data['tags'] if article_data['tags'] else [],
            'source': 'editorial',
            'date': date_iso,
            'timestamp': timestamp,
            'url': post_url
        }
        
        restored_posts.append(post)
        processed_files.append(filename)
        print(f"✅ Восстановлена статья: {post_id}")
        print(f"   Заголовок: {article_data['title'][:60]}...")
        print(f"   Теги: {', '.join(article_data['tags']) if article_data['tags'] else 'нет'}")
        print(f"   Дата: {date_iso}")
    
    # Добавляем восстановленные статьи в начало массива (они старше по дате)
    if restored_posts:
        # Сортируем по дате (старые первыми)
        restored_posts.sort(key=lambda x: x['timestamp'])
        
        # Объединяем со существующими постами
        all_posts = restored_posts + data['posts']
        
        # Сортируем все по дате (от старых к новым)
        all_posts.sort(key=lambda x: x['timestamp'])
        
        data['posts'] = all_posts
        
        print(f"\n✅ Восстановлено новых статей: {len(restored_posts)}")
        print(f"📊 Всего статей в blog-posts.json: {len(data['posts'])}")
    else:
        print("\n⚠️ Не найдено новых статей для восстановления")
        print("Все существующие HTML файлы уже есть в blog-posts.json")
    
    # Сохраняем обновлённый blog-posts.json
    if restored_posts:
        # Создаём backup
        backup_file = BLOG_POSTS_FILE.with_suffix('.json.backup')
        if BLOG_POSTS_FILE.exists():
            import shutil
            shutil.copy2(BLOG_POSTS_FILE, backup_file)
            print(f"✅ Создан backup: {backup_file.name}")
        
        with open(BLOG_POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ blog-posts.json обновлён")
        print(f"   Новый файл сохранён в: {BLOG_POSTS_FILE}")
    else:
        print("\n✅ blog-posts.json не изменился (все статьи уже есть)")
    
    print(f"\n📋 Обработано HTML файлов: {len(processed_files)}")
    for filename in processed_files:
        print(f"   - {filename}")

if __name__ == '__main__':
    main()
