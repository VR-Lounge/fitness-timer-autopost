#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Модуль для скачивания и загрузки изображений в Yandex Cloud
    
    Скачивает изображения из интернета, сохраняет локально
    и загружает в Yandex Cloud Object Storage для доступа из России.
    
    Автор: VR-Lounge
"""

import os
import re
import requests
import hashlib
from pathlib import Path
from urllib.parse import urlparse, urljoin
import subprocess
import time

from image_content_matcher import проверить_изображение_в_два_этапа

# Определяем пути
SCRIPT_DIR = Path(__file__).parent.absolute()
if (SCRIPT_DIR.parent / 'public_html').exists():
    REPO_ROOT = SCRIPT_DIR.parent
elif (SCRIPT_DIR / 'public_html').exists():
    REPO_ROOT = SCRIPT_DIR
else:
    REPO_ROOT = Path.cwd()
    if not (REPO_ROOT / 'public_html').exists():
        REPO_ROOT = REPO_ROOT.parent

BLOG_IMAGES_DIR = REPO_ROOT / 'public_html' / 'images' / 'blog'
BLOG_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Настройки Yandex Cloud
BUCKET_NAME = "www.tabatatimer.ru"
ENDPOINT_URL = "https://storage.yandexcloud.net"
YANDEX_ACCESS_KEY_ID = os.getenv('YANDEX_ACCESS_KEY_ID')
YANDEX_SECRET_ACCESS_KEY = os.getenv('YANDEX_SECRET_ACCESS_KEY')

def скачать_изображение(url, post_id=None):
    """
    Скачивает изображение из интернета и сохраняет локально
    
    Args:
        url: URL изображения
        post_id: ID поста для создания уникального имени файла
    
    Returns:
        tuple: (локальный_путь, yandex_url) или (None, None) при ошибке
    """
    try:
        # Проверяем, что это валидный URL
        if not url or not url.startswith(('http://', 'https://')):
            print(f"⚠️ Некорректный URL изображения: {url}")
            return None, None
        
        # Создаём уникальное имя файла
        parsed_url = urlparse(url)
        original_filename = os.path.basename(parsed_url.path)
        
        # Если нет расширения, пробуем определить по Content-Type
        if not original_filename or '.' not in original_filename:
            # Пробуем получить расширение из URL или используем .jpg по умолчанию
            original_filename = f"image_{int(time.time())}.jpg"
        
        # Создаём уникальное имя на основе URL и post_id
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        if post_id:
            filename = f"{post_id}_{url_hash}_{original_filename}"
        else:
            filename = f"{url_hash}_{original_filename}"
        
        # Очищаем имя файла от недопустимых символов
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        
        local_path = BLOG_IMAGES_DIR / filename
        
        # Если файл уже существует, возвращаем его
        if local_path.exists():
            print(f"✅ Изображение уже скачано: {filename}")
            yandex_url = f"https://www.tabatatimer.ru/images/blog/{filename}"
            return str(local_path), yandex_url
        
        # Скачиваем изображение
        print(f"📥 Скачиваю изображение: {url[:80]}...")
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': f"{parsed_url.scheme}://{parsed_url.netloc}/",
        }
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # Проверяем Content-Type
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            print(f"⚠️ URL не является изображением (Content-Type: {content_type})")
            return None, None
        
        # Сохраняем файл
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Изображение скачано: {filename} ({local_path.stat().st_size} bytes)")
        
        # Формируем URL для Yandex Cloud
        yandex_url = f"https://www.tabatatimer.ru/images/blog/{filename}"
        
        return str(local_path), yandex_url
        
    except Exception as e:
        print(f"❌ Ошибка при скачивании изображения {url}: {e}")
        return None, None

def загрузить_в_yandex_cloud(локальный_путь, yandex_путь=None):
    """
    Загружает изображение в Yandex Cloud Object Storage
    
    Args:
        локальный_путь: Путь к локальному файлу
        yandex_путь: Путь в Yandex Cloud (если None, используется имя файла)
    
    Returns:
        bool: True если успешно, False при ошибке
    """
    if not YANDEX_ACCESS_KEY_ID or not YANDEX_SECRET_ACCESS_KEY:
        print("⚠️ Переменные окружения YANDEX_ACCESS_KEY_ID и YANDEX_SECRET_ACCESS_KEY не установлены")
        print("   Изображение сохранено локально, но не загружено в Yandex Cloud")
        return False
    
    try:
        local_path = Path(локальный_путь)
        if not local_path.exists():
            print(f"❌ Файл не найден: {локальный_путь}")
            return False
        
        # Определяем путь в Yandex Cloud
        if yandex_путь is None:
            filename = local_path.name
            yandex_путь = f"images/blog/{filename}"
        
        # Загружаем через AWS CLI
        s3_path = f"s3://{BUCKET_NAME}/{yandex_путь}"
        
        print(f"☁️ Загружаю в Yandex Cloud: {yandex_путь}")
        
        env = os.environ.copy()
        env['AWS_ACCESS_KEY_ID'] = YANDEX_ACCESS_KEY_ID
        env['AWS_SECRET_ACCESS_KEY'] = YANDEX_SECRET_ACCESS_KEY
        env['AWS_DEFAULT_REGION'] = 'ru-central1'
        
        result = subprocess.run(
            [
                'aws', 's3', 'cp', str(local_path), s3_path,
                '--endpoint-url', ENDPOINT_URL,
                '--acl', 'public-read'
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"✅ Изображение загружено в Yandex Cloud: {yandex_путь}")
            return True
        else:
            print(f"❌ Ошибка загрузки в Yandex Cloud: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Таймаут при загрузке в Yandex Cloud")
        return False
    except Exception as e:
        print(f"❌ Ошибка при загрузке в Yandex Cloud: {e}")
        return False

def скачать_и_загрузить_изображение(
    url,
    post_id=None,
    *,
    заголовок: str = "",
    текст: str = "",
    теги: list = None,
    использованные_urls: list = None,
    строгий_фильтр: bool = True
):
    """
    Скачивает изображение и загружает в Yandex Cloud
    
    Args:
        url: URL изображения
        post_id: ID поста для создания уникального имени файла
    
    Returns:
        str: URL изображения в Yandex Cloud или оригинальный URL при ошибке
    """
    if not url:
        return None
    
    if использованные_urls is None:
        использованные_urls = []
    
    # ✅ УПРОЩЕНИЕ: Для skinnyms.com пропускаем проверку использованных URL
    # (изображения могут использоваться повторно в разных статьях)
    is_skinnyms = 'skinnyms.com' in url.lower()
    
    if not is_skinnyms:
        # Жёсткий фильтр: отбрасываем уже использованные URL (только для других источников)
        normalized_url = url.split('?')[0].lower()
        for existing_url in использованные_urls:
            if normalized_url == existing_url.split('?')[0].lower():
                print("❌ Анти‑повтор: изображение уже использовалось")
                return None
    
    # Предварительная проверка по DeepSeek (логотипы/текст/релевантность)
    # ✅ Для skinnyms.com пропускаем проверку DeepSeek
    if строгий_фильтр and not is_skinnyms:
        alt_текст = " ".join(теги) if теги else ""
        соответствует, оценка, объяснение = проверить_изображение_в_два_этапа(
            url, alt_текст, заголовок or "", текст or ""
        )
        if not соответствует:
            print(f"❌ DeepSeek (2 этапа) отклонил изображение: {объяснение}")
            return None
    
    # Скачиваем изображение
    локальный_путь, yandex_url = скачать_изображение(url, post_id)
    
    # ✅ Для skinnyms.com не отклоняем, если скачивание не удалось - вернём оригинальный URL
    if not локальный_путь:
        if is_skinnyms:
            print(f"⚠️ Не удалось скачать изображение для skinnyms.com, верну оригинальный URL")
            return url  # Возвращаем оригинальный URL для skinnyms.com
        print(f"⚠️ Не удалось скачать изображение, отклоняем")
        return None
    
    # Загружаем в Yandex Cloud (если есть креды), иначе используем локальный файл
    if not YANDEX_ACCESS_KEY_ID or not YANDEX_SECRET_ACCESS_KEY:
        print("⚠️ Yandex креды не заданы — использую локальный файл, загрузка будет позже")
        return yandex_url

    успех = загрузить_в_yandex_cloud(локальный_путь)
    if успех:
        return yandex_url
    return None

def загрузить_все_изображения_блога():
    """
    Загружает все изображения из папки images/blog/ в Yandex Cloud
    Используется для массовой загрузки после генерации постов
    """
    if not YANDEX_ACCESS_KEY_ID or not YANDEX_SECRET_ACCESS_KEY:
        print("⚠️ Переменные окружения YANDEX_ACCESS_KEY_ID и YANDEX_SECRET_ACCESS_KEY не установлены")
        return False
    
    if not BLOG_IMAGES_DIR.exists():
        print(f"⚠️ Папка с изображениями не найдена: {BLOG_IMAGES_DIR}")
        return False
    
    images = list(BLOG_IMAGES_DIR.glob('*.*'))
    if not images:
        print("ℹ️ Нет изображений для загрузки")
        return True
    
    print(f"📤 Загружаю {len(images)} изображений в Yandex Cloud...")
    
    env = os.environ.copy()
    env['AWS_ACCESS_KEY_ID'] = YANDEX_ACCESS_KEY_ID
    env['AWS_SECRET_ACCESS_KEY'] = YANDEX_SECRET_ACCESS_KEY
    env['AWS_DEFAULT_REGION'] = 'ru-central1'
    
    успешно = 0
    ошибок = 0
    
    for image_path in images:
        try:
            yandex_путь = f"images/blog/{image_path.name}"
            s3_path = f"s3://{BUCKET_NAME}/{yandex_путь}"
            
            result = subprocess.run(
                [
                    'aws', 's3', 'cp', str(image_path), s3_path,
                    '--endpoint-url', ENDPOINT_URL,
                    '--acl', 'public-read'
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                успешно += 1
            else:
                ошибок += 1
                print(f"❌ Ошибка загрузки {image_path.name}: {result.stderr[:100]}")
        except Exception as e:
            ошибок += 1
            print(f"❌ Ошибка при загрузке {image_path.name}: {e}")
    
    print(f"✅ Загружено: {успешно}, ошибок: {ошибок}")
    return ошибок == 0
