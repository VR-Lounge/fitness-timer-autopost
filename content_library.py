#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Библиотека высокорелевантного контента.
Хранит ссылки на статьи, изображения и краткие описания для повторного использования.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
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
