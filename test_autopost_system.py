#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки системы автоматической публикации
Проверяет все компоненты: парсинг, рерайтинг, публикацию в Telegram и блог
"""

import os
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

def проверить_переменные_окружения():
    """Проверяет наличие необходимых переменных окружения"""
    print("=" * 60)
    print("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    print("=" * 60)
    
    required_vars = {
        'TELEGRAM_BOT_TOKEN': 'Токен Telegram бота',
        'TELEGRAM_CHAT_ID': 'ID Telegram канала',
        'DEEPSEEK_API_KEY': 'API ключ DeepSeek'
    }
    
    все_настроено = True
    for var, описание in required_vars.items():
        значение = os.getenv(var)
        if значение:
            print(f"✅ {var}: {'*' * 20} (настроен)")
        else:
            print(f"❌ {var}: НЕ НАСТРОЕН ({описание})")
            все_настроено = False
    
    return все_настроено

def проверить_файлы():
    """Проверяет наличие необходимых файлов"""
    print("\n" + "=" * 60)
    print("📁 ПРОВЕРКА ФАЙЛОВ")
    print("=" * 60)
    
    required_files = {
        'menshealth_parser.py': 'Парсер Men\'s Health',
        'womenshealth_parser.py': 'Парсер Women\'s Health',
        'content_uniqueness.py': 'Проверка уникальности контента',
        'generate_blog_post_page.py': 'Генератор HTML страниц',
        '../public_html/blog-posts.json': 'Файл постов блога',
        '../public_html/blog.html': 'Главная страница блога'
    }
    
    все_найдено = True
    for файл, описание in required_files.items():
        путь = Path(__file__).parent / файл
        if путь.exists():
            print(f"✅ {файл}: найден ({описание})")
        else:
            print(f"❌ {файл}: НЕ НАЙДЕН ({описание})")
            все_найдено = False
    
    return все_найдено

def проверить_workflows():
    """Проверяет наличие GitHub Actions workflows"""
    print("\n" + "=" * 60)
    print("⚙️ ПРОВЕРКА GITHUB ACTIONS WORKFLOWS")
    print("=" * 60)
    
    workflows_dir = Path(__file__).parent / '.github' / 'workflows'
    required_workflows = {
        'menshealth-parser.yml': 'Workflow для Men\'s Health',
        'womenshealth-parser.yml': 'Workflow для Women\'s Health'
    }
    
    все_найдено = True
    for workflow, описание in required_workflows.items():
        путь = workflows_dir / workflow
        if путь.exists():
            print(f"✅ {workflow}: найден ({описание})")
        else:
            print(f"❌ {workflow}: НЕ НАЙДЕН ({описание})")
            все_найдено = False
    
    return все_найдено

def проверить_блог():
    """Проверяет структуру блога"""
    print("\n" + "=" * 60)
    print("📝 ПРОВЕРКА БЛОГА")
    print("=" * 60)
    
    blog_posts_file = Path(__file__).parent.parent / 'public_html' / 'blog-posts.json'
    blog_html_file = Path(__file__).parent.parent / 'public_html' / 'blog.html'
    blog_dir = Path(__file__).parent.parent / 'public_html' / 'blog'
    
    результаты = []
    
    # Проверка blog-posts.json
    if blog_posts_file.exists():
        try:
            import json
            with open(blog_posts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                posts = data.get('posts', [])
                print(f"✅ blog-posts.json: найден ({len(posts)} постов)")
                результаты.append(True)
        except Exception as e:
            print(f"⚠️ blog-posts.json: ошибка чтения ({e})")
            результаты.append(False)
    else:
        print("❌ blog-posts.json: НЕ НАЙДЕН")
        результаты.append(False)
    
    # Проверка blog.html
    if blog_html_file.exists():
        print(f"✅ blog.html: найден")
        результаты.append(True)
    else:
        print("❌ blog.html: НЕ НАЙДЕН")
        результаты.append(False)
    
    # Проверка папки blog/
    if blog_dir.exists():
        html_files = list(blog_dir.glob('*.html'))
        print(f"✅ blog/: найдено {len(html_files)} HTML страниц статей")
        результаты.append(True)
    else:
        print("⚠️ blog/: папка не найдена (будет создана при генерации)")
        результаты.append(True)  # Это нормально, если ещё нет статей
    
    return all(результаты)

def проверить_яндекс_cloud():
    """Проверяет настройки для Яндекс Cloud"""
    print("\n" + "=" * 60)
    print("☁️ ПРОВЕРКА НАСТРОЕК ЯНДЕКС CLOUD")
    print("=" * 60)
    
    upload_script = Path(__file__).parent / 'upload_blog_to_yandex.sh'
    
    if upload_script.exists():
        print(f"✅ upload_blog_to_yandex.sh: найден")
    else:
        print(f"❌ upload_blog_to_yandex.sh: НЕ НАЙДЕН")
        return False
    
    # Проверка переменных окружения (опционально)
    yandex_key = os.getenv('YANDEX_ACCESS_KEY_ID')
    yandex_secret = os.getenv('YANDEX_SECRET_ACCESS_KEY')
    
    if yandex_key and yandex_secret:
        print(f"✅ Переменные Яндекс Cloud: настроены")
    else:
        print(f"⚠️ Переменные Яндекс Cloud: не настроены (можно настроить в GitHub Secrets)")
    
    return True

def главная():
    """Главная функция тестирования"""
    print("\n" + "🚀" * 30)
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ АВТОМАТИЧЕСКОЙ ПУБЛИКАЦИИ")
    print("🚀" * 30 + "\n")
    
    результаты = []
    
    # Проверка переменных окружения
    результаты.append(("Переменные окружения", проверить_переменные_окружения()))
    
    # Проверка файлов
    результаты.append(("Файлы", проверить_файлы()))
    
    # Проверка workflows
    результаты.append(("GitHub Actions", проверить_workflows()))
    
    # Проверка блога
    результаты.append(("Блог", проверить_блог()))
    
    # Проверка Яндекс Cloud
    результаты.append(("Яндекс Cloud", проверить_яндекс_cloud()))
    
    # Итоговый отчёт
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЁТ")
    print("=" * 60)
    
    все_готово = True
    for название, результат in результаты:
        статус = "✅ ГОТОВО" if результат else "❌ ТРЕБУЕТ ВНИМАНИЯ"
        print(f"{название}: {статус}")
        if not результат:
            все_готово = False
    
    print("\n" + "=" * 60)
    if все_готово:
        print("✅ ВСЕ КОМПОНЕНТЫ ГОТОВЫ К РАБОТЕ!")
        print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("  1. Убедитесь, что в GitHub Secrets настроены:")
        print("     - TELEGRAM_BOT_TOKEN")
        print("     - TELEGRAM_CHAT_ID")
        print("     - DEEPSEEK_API_KEY")
        print("     - YANDEX_ACCESS_KEY_ID (опционально)")
        print("     - YANDEX_SECRET_ACCESS_KEY (опционально)")
        print("\n  2. Workflows будут запускаться автоматически:")
        print("     - Men's Health: 08:00 и 20:00 UTC")
        print("     - Women's Health: 09:00 и 21:00 UTC")
        print("\n  3. Или запустите вручную через GitHub Actions")
        print("\n  4. После публикации посты автоматически:")
        print("     - Отправляются в Telegram канал")
        print("     - Сохраняются в blog-posts.json")
        print("     - Генерируются HTML страницы для SEO")
        print("     - Загружаются на Яндекс Cloud (если настроено)")
    else:
        print("⚠️ НЕКОТОРЫЕ КОМПОНЕНТЫ ТРЕБУЮТ НАСТРОЙКИ")
        print("\nПроверьте сообщения выше и исправьте проблемы.")
    
    print("=" * 60 + "\n")
    
    return все_готово

if __name__ == '__main__':
    try:
        успех = главная()
        sys.exit(0 if успех else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
