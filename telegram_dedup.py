#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Жёсткая защита от повторов в Telegram (текст + изображение).
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urlparse


STATE_FILE = Path(".telegram_recent.json")
PUBLICATION_LOG_FILE = Path(".publication_logs.json")


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.lower().split())


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def _hash_text(text: str) -> str:
    return hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()


def load_recent() -> Dict:
    if not STATE_FILE.exists():
        return {"items": []}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": []}


def save_recent(data: Dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_recent_images_from_logs(max_items: int) -> Set[str]:
    if not PUBLICATION_LOG_FILE.exists():
        return set()
    try:
        with open(PUBLICATION_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        images = []
        for item in logs[-max_items:]:
            url = _normalize_url(item.get("image_url", ""))
            if url:
                images.append(url)
        return set(images)
    except Exception:
        return set()


def is_duplicate(text: str, image_url: str, max_items: int = 30) -> bool:
    recent = load_recent()
    text_hash = _hash_text(text)
    image_norm = _normalize_url(image_url)
    log_images = _load_recent_images_from_logs(max_items)
    for item in recent.get("items", [])[-max_items:]:
        if item.get("text_hash") == text_hash:
            return True
        if image_norm and item.get("image_url") == image_norm:
            return True
    if image_norm and image_norm in log_images:
        return True
    return False


def record_post(text: str, image_url: str, max_items: int = 30) -> None:
    recent = load_recent()
    text_hash = _hash_text(text)
    image_norm = _normalize_url(image_url)
    recent.setdefault("items", []).append({
        "text_hash": text_hash,
        "image_url": image_norm,
        "created_at": datetime.now().isoformat()
    })
    if len(recent["items"]) > max_items:
        recent["items"] = recent["items"][-max_items:]
    save_recent(recent)
