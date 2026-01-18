#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Модуль для работы с коллекциями изображений Fitness | Woman и Fitness | Man
    
    Предоставляет функции для получения уникальных изображений из коллекций,
    которые находятся на Яндекс Cloud.
    
    Автор: VR-Lounge
"""

import os
import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

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

# Пути к manifest.json коллекций
WOMAN_MANIFEST = REPO_ROOT / 'public_html' / 'images' / 'Fitness | Woman' / 'manifest.json'
MAN_MANIFEST = REPO_ROOT / 'public_html' / 'images' / 'Fitness | Man' / 'manifest.json'

# Базовый URL для изображений на Яндекс Cloud
BASE_IMAGE_URL = "https://www.tabatatimer.ru/images"

def загрузить_manifest(путь_к_manifest: Path) -> Optional[Dict]:
    """
    Загружает manifest.json коллекции изображений
    
    Args:
        путь_к_manifest: Путь к файлу manifest.json
    
    Returns:
        Словарь с данными manifest или None при ошибке
    """
    try:
        if not путь_к_manifest.exists():
            print(f"⚠️ Manifest не найден: {путь_к_manifest}")
            return None
        
        with open(путь_к_manifest, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки manifest: {e}")
        return None

def получить_все_изображения_из_коллекции(коллекция: str = 'woman') -> List[Dict]:
    """
    Получает список всех изображений из указанной коллекции
    
    Args:
        коллекция: 'woman' или 'man'
    
    Returns:
        Список словарей с информацией об изображениях
    """
    if коллекция.lower() == 'woman':
        manifest_path = WOMAN_MANIFEST
        коллекция_путь = 'Fitness | Woman'
    elif коллекция.lower() == 'man':
        manifest_path = MAN_MANIFEST
        коллекция_путь = 'Fitness | Man'
    else:
        print(f"⚠️ Неизвестная коллекция: {коллекция}")
        return []
    
    manifest = загрузить_manifest(manifest_path)
    if not manifest:
        return []
    
    items = manifest.get('items', [])
    изображения = []
    
    for item in items:
        filename = item.get('file', '')
        if not filename:
            continue
        
        # Формируем URL изображения на Яндекс Cloud
        # Заменяем пробелы и специальные символы в пути
        коллекция_url = коллекция_путь.replace(' ', '%20')
        image_url = f"{BASE_IMAGE_URL}/{коллекция_url}/{filename}"
        
        изображения.append({
            'url': image_url,
            'file': filename,
            'alt': item.get('alt', ''),
            'title': item.get('alt', ''),
            'collection': коллекция
        })
    
    return изображения

def получить_уникальное_изображение_из_коллекции(
    коллекция: str,
    использованные_urls: List[str] = None,
    тема: str = None
) -> Optional[Dict]:
    """
    Получает уникальное изображение из коллекции, которое еще не использовалось
    
    Args:
        коллекция: 'woman' или 'man'
        использованные_urls: Список URL изображений, которые уже использованы
        тема: Тема статьи (для более релевантного выбора)
    
    Returns:
        Словарь с информацией об изображении или None
    """
    if использованные_urls is None:
        использованные_urls = []
    
    все_изображения = получить_все_изображения_из_коллекции(коллекция)
    if not все_изображения:
        print(f"⚠️ Коллекция {коллекция} пуста или не найдена")
        return None
    
    # Фильтруем уже использованные изображения
    доступные = []
    for img in все_изображения:
        img_url = img.get('url', '')
        if not img_url:
            continue
        
        # Проверяем, не использовано ли это изображение
        используется = False
        for used_url in использованные_urls:
            # Нормализуем URL для сравнения
            normalized_used = used_url.split('?')[0].lower()
            normalized_img = img_url.split('?')[0].lower()
            
            # Проверяем по полному URL или по имени файла
            if normalized_used == normalized_img or used_url.endswith(img.get('file', '')):
                используется = True
                break
        
        if not используется:
            доступные.append(img)
    
    if not доступные:
        print(f"⚠️ Все изображения из коллекции {коллекция} уже использованы")
        # Если все использованы, возвращаем случайное (но это не идеально)
        return random.choice(все_изображения) if все_изображения else None
    
    # Выбираем случайное изображение из доступных для разнообразия
    выбранное = random.choice(доступные)
    
    print(f"✅ Выбрано изображение из коллекции {коллекция}: {выбранное.get('file', '')}")
    return выбранное

def получить_релевантное_изображение_для_статьи(
    заголовок: str,
    текст: str,
    теги: List[str] = None,
    использованные_urls: List[str] = None
) -> Optional[Dict]:
    """
    Выбирает релевантное изображение из коллекций на основе темы статьи
    
    Args:
        заголовок: Заголовок статьи
        текст: Текст статьи (первые 500 символов)
        теги: Теги статьи
        использованные_urls: Список уже использованных URL
    
    Returns:
        Словарь с информацией об изображении или None
    """
    if использованные_urls is None:
        использованные_urls = []
    
    # Определяем, какую коллекцию использовать
    # Если есть тег "ДЕВУШКАМ" или текст содержит женские маркеры - используем woman
    # Если есть тег "МУЖЧИНАМ" или текст содержит мужские маркеры - используем man
    # Иначе - чередуем для разнообразия
    
    текст_нижний = (заголовок + ' ' + текст[:500]).lower()
    теги_нижний = [t.lower() for t in (теги or [])]
    
    использовать_woman = False
    использовать_man = False
    
    if 'девушкам' in теги_нижний or any(маркер in текст_нижний for маркер in ['девушк', 'женщин', 'женск']):
        использовать_woman = True
    elif 'мужчинам' in теги_нижний or any(маркер in текст_нижний for маркер in ['мужчин', 'мужск']):
        использовать_man = True
    else:
        # Если не определено, чередуем
        # Используем хеш заголовка для детерминированного выбора
        import hashlib
        hash_value = int(hashlib.md5(заголовок.encode()).hexdigest(), 16)
        использовать_woman = (hash_value % 2 == 0)
        использовать_man = not использовать_woman
    
    # Пробуем получить изображение из нужной коллекции
    if использовать_woman:
        изображение = получить_уникальное_изображение_из_коллекции('woman', использованные_urls)
        if изображение:
            return изображение
    
    if использовать_man:
        изображение = получить_уникальное_изображение_из_коллекции('man', использованные_urls)
        if изображение:
            return изображение
    
    # Если не получилось, пробуем другую коллекцию
    if использовать_woman:
        изображение = получить_уникальное_изображение_из_коллекции('man', использованные_urls)
    else:
        изображение = получить_уникальное_изображение_из_коллекции('woman', использованные_urls)
    
    return изображение
