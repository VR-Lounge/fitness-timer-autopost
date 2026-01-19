#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер SkinnyMs (категория Fitness) для наполнения content_library.json.
Сканирует страницы категории, собирает статьи и извлекает текст + изображения.
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from content_library import load_library, save_library, upsert_item, build_library_item, normalize_images


STATE_FILE = Path(".skinnyms_queue.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://skinnyms.com/"
}

BLOCKED_IMAGE_URLS = {
    "https://skinnyms.com/wp-content/uploads/2024/11/Skinny-Ms-Graphics-Horizontal.png"
}

BLOCKED_IMAGE_KEYWORDS = [
    "graphics", "horizontal", "banner", "bundle", "promo", "cta", "button",
    "ad-", "advert", "logo", "skinny-ms-graphics", "skinnyms-graphics"
]


def load_state() -> Dict:
    if not STATE_FILE.exists():
        return {"pending": [], "seen_urls": [], "last_page_scanned": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"pending": [], "seen_urls": [], "last_page_scanned": {}}


def save_state(state: Dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_page(url: str, retries: int = 3) -> Optional[BeautifulSoup]:
    for i in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"⚠️ Ошибка при загрузке {url}: {e}")
            if i < retries - 1:
                time.sleep(2)
    return None


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def is_branded_image(url: str, alt: str = "", width: str = "", height: str = "") -> bool:
    if not url:
        return True
    clean = url.split("?")[0]
    if clean in BLOCKED_IMAGE_URLS:
        return True
    lower = clean.lower()
    if any(k in lower for k in BLOCKED_IMAGE_KEYWORDS):
        return True
    alt_lower = (alt or "").lower()
    if "skinnyms" in alt_lower and "logo" in alt_lower:
        return True
    try:
        w = int(width) if width else None
        h = int(height) if height else None
        if w == 1200 and h == 600:
            return True
    except Exception:
        pass
    return False


def extract_img_url(img) -> str:
    if img.has_attr("data-src"):
        return img["data-src"]
    if img.has_attr("data-lazy-src"):
        return img["data-lazy-src"]
    if img.has_attr("data-srcset"):
        return img["data-srcset"].split(",")[0].strip().split(" ")[0]
    if img.has_attr("srcset"):
        return img["srcset"].split(",")[0].strip().split(" ")[0]
    return img.get("src", "")


def collect_article_links(soup: BeautifulSoup) -> List[str]:
    links = []
    for a in soup.select("h2.entry-title a, h3.entry-title a, .entry-title a, .post-title a"):
        href = a.get("href")
        if not href:
            continue
        if "skinnyms.com" not in href:
            href = urljoin(BASE_CATEGORY_URL, href)
        if "/category/" in href:
            continue
        links.append(normalize_url(href))
    return list(dict.fromkeys(links))


def parse_article(url: str) -> Optional[Dict]:
    soup = fetch_page(url)
    if not soup:
        return None
    title_el = soup.select_one("h1.entry-title, h1.post-title, h1")
    title = title_el.get_text(strip=True) if title_el else ""

    content = soup.select_one(".entry-content, .post-content, article .entry-content, article")
    if not content:
        return None

    # Featured image (og:image fallback)
    featured_url = ""
    og = soup.select_one("meta[property='og:image']")
    if og and og.get("content"):
        featured_url = og["content"]

    images = []
    for img in content.select("img"):
        img_url = extract_img_url(img)
        if not img_url:
            continue
        if "gravatar.com" in img_url:
            continue
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        elif img_url.startswith("/"):
            img_url = urljoin(url, img_url)
        if "skinnyms.com/wp-content/uploads" not in img_url:
            continue
        alt = img.get("alt", "")
        width = img.get("width", "")
        height = img.get("height", "")
        if is_branded_image(img_url, alt, width, height):
            continue
        images.append({
            "url": img_url,
            "alt": alt,
            "title": alt,
            "is_main": False
        })

    if featured_url and not is_branded_image(featured_url):
        images.insert(0, {"url": featured_url, "alt": title, "title": title, "is_main": True})

    images = normalize_images(images)

    text = content.get_text("\n", strip=True)
    excerpt = re.sub(r"\s+", " ", text)[:3000]

    return {
        "title": title,
        "url": url,
        "content_excerpt": excerpt,
        "images": images
    }


def main() -> None:
    max_pages = int(os.getenv("SKINNYMS_MAX_PAGES", "79"))
    pages_per_run = int(os.getenv("SKINNYMS_PAGES_PER_RUN", "79"))
    max_articles = int(os.getenv("SKINNYMS_MAX_ARTICLES_PER_RUN", "20"))
    categories_env = os.getenv("SKINNYMS_CATEGORIES", "fitness,recipes")
    categories = [c.strip() for c in categories_env.split(",") if c.strip()]
    category_map = {
        "fitness": {
            "base_url": "https://skinnyms.com/category/fitness/",
            "source": "skinnyms_fitness",
            "keywords": ["fitness", "workout", "hiit", "tabata", "emom", "amrap"]
        },
        "recipes": {
            "base_url": "https://skinnyms.com/category/recipes/",
            "source": "skinnyms_recipes",
            "keywords": ["recipes", "healthy", "meal", "nutrition"]
        }
    }

    state = load_state()
    library = load_library()

    for category in categories:
        cfg = category_map.get(category)
        if not cfg:
            print(f"⚠️ Неизвестная категория: {category}")
            continue
        base_url = cfg["base_url"]
        last_page = int(state.get("last_page_scanned", {}).get(category, 0))
        start_page = max(1, last_page + 1)
        end_page = min(max_pages, start_page + pages_per_run - 1)

        print(f"🔎 {category}: страницы {start_page}-{end_page} из {max_pages}")
        for page in range(start_page, end_page + 1):
            page_url = base_url if page == 1 else f"{base_url}page/{page}/"
            soup = fetch_page(page_url)
            if not soup:
                continue
            links = collect_article_links(soup)
            for link in links:
                if link not in state["seen_urls"]:
                    state["pending"].append({
                        "url": link,
                        "source": cfg["source"],
                        "rss_feed_url": base_url,
                        "keywords": cfg["keywords"]
                    })
            state.setdefault("last_page_scanned", {})[category] = page
            time.sleep(1)

    save_state(state)
    print(f"📌 В очереди статей: {len(state['pending'])}")

    processed = 0
    while state["pending"] and processed < max_articles:
        item = state["pending"].pop(0)
        url = item.get("url")
        source = item.get("source", "skinnyms_fitness")
        rss_feed_url = item.get("rss_feed_url", "")
        keywords = item.get("keywords", [])
        if not url or url in state["seen_urls"]:
            continue
        print(f"\n📝 Парсинг: {url}")
        parsed = parse_article(url)
        state["seen_urls"].append(url)
        if not parsed:
            continue
        print(f"✅ Заголовок: {parsed['title']}")
        print(f"🖼️  Изображений: {len(parsed['images'])}")
        for idx, img in enumerate(parsed["images"][:10], 1):
            print(f"   {idx}. {img.get('url','')}")

        item = build_library_item(
            title=parsed["title"],
            url=parsed["url"],
            rss_feed_url=rss_feed_url,
            source=source,
            keywords=keywords,
            summary_ru="",
            relevance_score=85,
            content_excerpt=parsed["content_excerpt"],
            images=parsed["images"]
        )
        upsert_item(library, item)
        processed += 1
        time.sleep(1)

    save_library(library)
    save_state(state)
    print(f"\n✅ Добавлено в библиотеку: {processed} статей")


if __name__ == "__main__":
    main()
