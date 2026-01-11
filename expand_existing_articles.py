#!/usr/bin/env python3
"""
Скрипт для расширения контента существующих статей в blog-posts.json
до полноценных статей (2000-4000 символов) через DeepSeek AI
"""

import json
import os
import sys
from pathlib import Path
import requests

# Добавляем путь к модулям
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# Импортируем функцию расширения контента
try:
    from menshealth_parser import расширить_контент_для_статьи
    # Пытаемся получить DEEPSEEK_API_KEY из модуля
    import menshealth_parser
    DEEPSEEK_API_KEY_FROM_MODULE = getattr(menshealth_parser, 'DEEPSEEK_API_KEY', None)
except ImportError as e:
    print(f"❌ Не удалось импортировать функции из menshealth_parser.py: {e}")
    sys.exit(1)

# Путь к blog-posts.json
REPO_ROOT = None
if (SCRIPT_DIR.parent / 'public_html').exists():
    REPO_ROOT = SCRIPT_DIR.parent
elif (Path.cwd().parent / 'public_html').exists():
    REPO_ROOT = Path.cwd().parent
else:
    REPO_ROOT = Path.cwd()

BLOG_POSTS_FILE = REPO_ROOT / 'public_html' / 'blog-posts.json'

def main():
    """Расширяет контент существующих статей"""
    print("=" * 60)
    print("📝 РАСШИРЕНИЕ КОНТЕНТА СУЩЕСТВУЮЩИХ СТАТЕЙ")
    print("=" * 60)
    
    if not BLOG_POSTS_FILE.exists():
        print(f"❌ Файл не найден: {BLOG_POSTS_FILE}")
        return
    
    # Проверяем наличие DEEPSEEK_API_KEY
    api_key = os.getenv('DEEPSEEK_API_KEY') or DEEPSEEK_API_KEY_FROM_MODULE
    if not api_key:
        print("❌ DEEPSEEK_API_KEY не настроен")
        print("   Проверьте переменные окружения или настройки в menshealth_parser.py")
        print("   Установите: export DEEPSEEK_API_KEY='ваш_ключ'")
        return
    
    print(f"✅ DEEPSEEK_API_KEY найден\n")
    
    # Загружаем существующие посты
    with open(BLOG_POSTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    posts = data.get('posts', [])
    print(f"\n📋 Найдено статей: {len(posts)}\n")
    
    # Анализируем и расширяем статьи
    обновлено = 0
    пропущено = 0
    
    for idx, post in enumerate(posts, 1):
        post_id = post.get('id', 'unknown')
        title = post.get('title', 'Статья')
        текущий_текст = post.get('text', '')
        длина_текста = len(текущий_текст)
        
        print(f"[{idx}/{len(posts)}] {post_id}: {длина_текста} символов")
        print(f"   Заголовок: {title[:60]}...")
        
        # Если текст уже достаточно длинный (>= 2000 символов), пропускаем
        if длина_текста >= 2000:
            print(f"   ✅ Текст уже достаточно длинный, пропускаем\n")
            пропущено += 1
            continue
        
        # Расширяем контент через DeepSeek
        print(f"   📝 Расширяю контент через DeepSeek AI...")
        try:
            расширенный_текст = расширить_контент_для_статьи(текущий_текст, title)
            
            if расширенный_текст and len(расширенный_текст) > длина_текста:
                # Обновляем текст статьи
                post['text'] = расширенный_текст
                обновлено += 1
                print(f"   ✅ Контент расширен: {len(расширенный_текст)} символов (+{len(расширенный_текст) - длина_текста})\n")
            else:
                print(f"   ⚠️ Не удалось расширить контент, оставляем как есть\n")
                пропущено += 1
        except Exception as e:
            print(f"   ❌ Ошибка при расширении: {e}\n")
            пропущено += 1
    
    # Сохраняем обновлённый blog-posts.json
    if обновлено > 0:
        print(f"\n💾 Сохраняю обновлённый blog-posts.json...")
        BLOG_POSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BLOG_POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Обновлено статей: {обновлено}")
        print(f"⏭️ Пропущено статей: {пропущено}")
        print(f"\n📄 Файл сохранён: {BLOG_POSTS_FILE}")
        
        # Регенерируем HTML страницы
        print(f"\n🔄 Регенерирую HTML страницы...")
        генератор = SCRIPT_DIR / 'generate_blog_post_page.py'
        if генератор.exists():
            import subprocess
            result = subprocess.run(
                ['python3', str(генератор)],
                cwd=str(REPO_ROOT / 'public_html'),
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                print("✅ HTML страницы регенерированы")
                if result.stdout:
                    print(result.stdout)
            else:
                print(f"⚠️ Ошибка регенерации: {result.stderr}")
                if result.stdout:
                    print(f"Вывод: {result.stdout}")
    else:
        print(f"\n✅ Все статьи уже имеют достаточно длинный контент")
        print(f"⏭️ Пропущено: {пропущено}")

if __name__ == '__main__':
    main()
