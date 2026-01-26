#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Библиотека высокорелевантного контента.
Хранит ссылки на статьи, изображения и краткие описания для повторного использования.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


LIBRARY_FILE = Path(__file__).parent / "content_library.json"


def _default_library() -> Dict:
    return {
        "version": 1,
        "updated_at": datetime.now().isoformat(),
        "items": []
    }


def load_library() -> Dict:
    if not LIBRARY_FILE.exists():
        return _default_library()
    try:
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "items" not in data:
            return _default_library()
        return data
    except Exception:
        return _default_library()


def save_library(data: Dict) -> None:
    data["updated_at"] = datetime.now().isoformat()
    with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def upsert_item(library: Dict, item: Dict) -> bool:
    """Добавляет или обновляет запись в библиотеке. Возвращает True если добавлено/обновлено."""
    if not item.get("url"):
        return False
    normalized = normalize_url(item["url"])
    for existing in library.get("items", []):
        if normalize_url(existing.get("url", "")) == normalized:
            existing.update(item)
            return True
    library.setdefault("items", []).append(item)
    return True


def _normalize_image_url(url: str) -> str:
    """Нормализует URL изображения, удаляя query параметры и размеры из имени файла."""
    if not url:
        return ""
    parsed = urlparse(url)
    path = parsed.path
    
    # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Удаляем размеры из имени файла
    # Например: "image-600x400.jpg" -> "image.jpg"
    # Паттерны: -600x400, -750x500, -1200x800, -1200x1802 и т.д.
    import re
    # Удаляем паттерны типа -600x400, -750x500 перед расширением
    path = re.sub(r'-\d+x\d+(?=\.[a-zA-Z]+$)', '', path)
    # Также удаляем варианты типа -e1234567890 (timestamp в имени)
    path = re.sub(r'-e\d+(?=\.[a-zA-Z]+$)', '', path)
    
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def normalize_images(images: List[Dict]) -> List[Dict]:
    """Удаляет дубликаты изображений по нормализованному URL (без размеров в имени файла).
    Если есть несколько вариантов одного изображения (с размерами и без), предпочитает вариант без размера."""
    if not images:
        return []
    # Группируем изображения по нормализованному URL
    groups = {}
    for img in images:
        if not isinstance(img, dict):
            continue
        url = img.get("url", "")
        key = _normalize_image_url(url)
        if not key:
            continue
        if key not in groups:
            groups[key] = []
        groups[key].append(img)
    
    # Для каждой группы выбираем лучшее изображение (предпочитаем без размеров в имени)
    normalized = []
    for key, group in groups.items():
        if len(group) == 1:
            normalized.append(group[0])
        else:
            # Если есть несколько вариантов, выбираем тот, у которого в URL нет размеров (например, -600x400)
            import re
            best = None
            for img in group:
                url = img.get("url", "")
                # Проверяем, есть ли размеры в имени файла
                if not re.search(r'-\d+x\d+(?=\.[a-zA-Z]+$)', url):
                    best = img
                    break
            # Если не нашли без размеров, берем первое
            if not best:
                best = group[0]
            normalized.append(best)
    
    return normalized


def prune_library(
    library: Dict,
    *,
    min_score: int = 70,
    min_images: int = 1,
    blocked_phrases: Optional[List[str]] = None
) -> Tuple[Dict, int]:
    """Удаляет нерелевантные записи из библиотеки."""
    removed = 0
    if blocked_phrases is None:
        blocked_phrases = [
            "розыгрыш", "giveaway", "абонемент", "membership",
            "анонс", "расписание", "призыв к регистрации", "register",
            "скидк", "sale", "promo"
        ]
    
    cleaned = []
    for item in library.get("items", []):
        score = item.get("relevance_score")
        summary = (item.get("summary_ru", "") or "").lower()
        content_excerpt = (item.get("content_excerpt", "") or "").lower()
        images = normalize_images(item.get("images", []))
        
        if score is not None and score < min_score:
            removed += 1
            continue
        
        if any(p in summary or p in content_excerpt for p in blocked_phrases):
            removed += 1
            continue
        
        if len(images) < min_images:
            removed += 1
            continue
        
        item["images"] = images
        cleaned.append(item)
    
    library["items"] = cleaned
    return library, removed


def build_library_item(
    *,
    title: str,
    url: str,
    rss_feed_url: str,
    source: str,
    keywords: Optional[List[str]] = None,
    summary_ru: Optional[str] = None,
    relevance_score: Optional[int] = None,
    content_excerpt: Optional[str] = None,
    images: Optional[List[Dict]] = None
) -> Dict:
    domain = urlparse(url).netloc.lower() if url else ""
    return {
        "id": f"{source}_{hash(normalize_url(url))}",
        "title": title,
        "url": url,
        "rss_feed_url": rss_feed_url,
        "domain": domain,
        "source": source,
        "keywords": keywords or [],
        "summary_ru": summary_ru or "",
        "relevance_score": relevance_score,
        "content_excerpt": content_excerpt or "",
        "images": images or [],
        "fetched_at": datetime.now().isoformat()
    }
