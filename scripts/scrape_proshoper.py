#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер акционных цен ProShoper.ru (Пятёрочка, Москва)

Технологии:
- requests + BeautifulSoup4 (без Selenium)
- статичный HTML-парсинг

Выход:
- grocery_prices.json (список товаров с ценами)

ВАЖНО:
- Скрипт устойчив к ошибкам (если сайт недоступен — не ломаем данные).
- Все логи на русском языке.
"""

from __future__ import annotations

import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# requests / bs4 могут быть не установлены локально — graceful degradation
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False
    print("⚠️ requests не установлен — парсинг отключён (graceful режим).")

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None
    BS4_AVAILABLE = False
    print("⚠️ beautifulsoup4 не установлен — парсинг отключён (graceful режим).")


# Парсим категории с ProShoper.ru (в промпте URL одинаковые — оставляем как есть)
CATEGORIES = {
    "Фрукты, овощи, зелень": "https://proshoper.ru/actions/pyaterochka/moskva/",
    "Молоко, сыр, яйца": "https://proshoper.ru/actions/pyaterochka/moskva/",
    "Мясо, рыба, колбасы": "https://proshoper.ru/actions/pyaterochka/moskva/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

OUT_FILE = Path("grocery_prices.json")


def _parse_price(text: str) -> Optional[float]:
    """Очищает цену вида '139.99 ₽' / '139,99 ₽' → 139.99"""
    if not text:
        return None
    s = text.replace("\xa0", " ").strip()
    s = s.replace("₽", "").replace("руб.", "").replace("руб", "").strip()
    s = s.replace(" ", "")
    s = s.replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None


def _guess_unit(name: str) -> str:
    """
    Примитивное определение единицы измерения.
    Если указано 'кг' — считаем кг, иначе шт.
    """
    s = (name or "").lower()
    if "кг" in s:
        return "кг"
    return "шт"


def _calc_discount(price: Optional[float], old_price: Optional[float]) -> Optional[str]:
    if price is None or old_price is None or old_price <= 0:
        return None
    d = round((old_price - price) / old_price * 100)
    return f"{d}%" if d != 0 else "0%"


def _fetch_html(url: str) -> Optional[str]:
    if not REQUESTS_AVAILABLE:
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"❌ Ошибка загрузки {url}: {e}")
        return None


def _parse_products_from_html(html: str, category: str) -> List[Dict[str, Any]]:
    if not BS4_AVAILABLE or not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    products: List[Dict[str, Any]] = []

    # ProShoper структура (ориентир из промпта):
    # <article id="id_product_XXX">
    #   <div class="price_new">139.99 ₽</div>
    #   <div class="price_old">159.99 ₽</div>
    #   <div class="name">Яблоки ...</div>
    # </article>
    for article in soup.find_all("article"):
        try:
            name_el = article.find(class_="name")
            price_el = article.find(class_="price_new")
            old_el = article.find(class_="price_old")

            name = (name_el.get_text(" ", strip=True) if name_el else "").strip()
            if not name:
                continue

            price = _parse_price(price_el.get_text(" ", strip=True) if price_el else "")
            old_price = _parse_price(old_el.get_text(" ", strip=True) if old_el else "")
            discount = _calc_discount(price, old_price)
            unit = _guess_unit(name)

            if price is None:
                # без новой цены товар бесполезен
                continue

            products.append(
                {
                    "name": name,
                    "category": category,
                    "price": price,
                    "old_price": old_price,
                    "discount": discount,
                    "unit": unit,
                }
            )
        except Exception:
            # не ломаемся из-за одного товара
            continue

    return products


def _load_existing() -> Dict[str, Any]:
    if OUT_FILE.exists():
        try:
            return json.loads(OUT_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: Dict[str, Any]) -> None:
    OUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    print("🔍 Начинаем парсинг ProShoper.ru...")

    existing = _load_existing()

    if not (REQUESTS_AVAILABLE and BS4_AVAILABLE):
        # graceful: не портим существующий файл
        if not OUT_FILE.exists():
            data = {
                "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "source": "ProShoper.ru",
                "store": "Пятёрочка",
                "city": "Москва",
                "products": [],
            }
            _save(data)
            print("💾 Создан пустой grocery_prices.json (graceful режим)")
        else:
            print("⚠️ Парсинг пропущен (нет зависимостей). Существующие данные не изменены.")
        return 0

    all_products: List[Dict[str, Any]] = []

    for cat, url in CATEGORIES.items():
        print(f"📂 Категория: {cat}")
        html = _fetch_html(url)
        if not html:
            print(f"⚠️ Не удалось загрузить категорию: {cat}")
            continue

        products = _parse_products_from_html(html, cat)
        print(f"✅ Спарсено: {len(products)} товаров")
        all_products.extend(products)

        # Задержка 1–2 сек между запросами
        time.sleep(1 + random.random())

    if not all_products:
        print("⚠️ Товары не найдены. Оставляем существующие данные без изменений.")
        return 0

    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "ProShoper.ru",
        "store": "Пятёрочка",
        "city": "Москва",
        "products": all_products,
    }

    _save(data)
    print("💾 Сохранено в grocery_prices.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


