#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сопоставление ингредиентов из recipes_prices.json с товарами из grocery_prices.json (ProShoper)

Задача:
- Читать recipes_prices.json (существующий файл)
- Читать grocery_prices.json (новый файл с акциями)
- Искать совпадения по названиям (нечёткий поиск + словарь)
- Обновлять цены в recipes_prices.json
- Писать источник: "Пятёрочка (ProShoper)"
- Выводить статистику

Важно:
- Не ломаем данные, если grocery_prices.json пуст/недоступен (graceful).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RECIPES_FILE = Path("recipes_prices.json")
GROCERY_FILE = Path("grocery_prices.json")


# Словарь маппинга (из промпта)
INGREDIENT_MAPPING = {
    "яйца": ["яйцо", "яйца", "яйца куриные", "яйца с0", "яйца с1", "яйца с 0", "яйца с 1"],
    "молоко": ["молоко 3.2%", "молоко ультрапастеризованное", "молоко пастеризованное", "молоко"],
    "творог 5%": ["творог 5%", "творог бзмж 5%", "творог"],
    "куриная грудка": ["грудка куриная", "филе куриное грудки", "грудка охлажденная", "филе куриное", "куриная грудка"],
    "гречка": ["гречка ядрица", "крупа гречневая", "гречка"],
    "овсяные хлопья": ["овсянка", "хлопья овсяные", "геркулес", "овсяные хлопья"],
    "рис": ["рис круглозерный", "рис длиннозерный", "рис"],
    "томат": ["помидор", "томаты", "помидоры", "томат"],
    "огурец": ["огурцы", "огурец"],
    "лук": ["лук репчатый", "лук"],
    "морковь": ["морковь"],
    "банан": ["бананы", "банан"],
    "авокадо": ["авокадо"],
    "шпинат": ["шпинат замороженный", "шпинат свежий", "шпинат"],
    "брокколи": ["брокколи замороженная", "брокколи"],
    "киноа": ["крупа киноа", "киноа"],
    "рыба": ["минтай", "хек", "треска", "семга", "сёмга", "рыба"],
    "индейка": ["филе индейки", "индейка охлажденная", "индейка"],
}


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace("ё", "е")
    s = re.sub(r"[^0-9a-zа-я\\s]", " ", s)
    s = re.sub(r"\\s+", " ", s).strip()
    return s


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _parse_amount(amount: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Пытаемся извлечь количество и единицу из amount.
    Примеры:
      '2 шт.' -> (2, 'шт')
      '150 г' -> (150, 'г')
      '0.5 л' -> (0.5, 'л')
      '1/2 шт.' -> (0.5, 'шт')
    """
    s = (amount or "").lower().replace(",", ".").strip()
    if not s:
        return None, None
    # дробь 1/2
    m = re.search(r"(\\d+)\\s*/\\s*(\\d+)", s)
    if m:
        val = float(m.group(1)) / float(m.group(2))
        unit = _guess_unit_from_amount(s)
        return val, unit
    m = re.search(r"(\\d+(?:\\.\\d+)?)", s)
    if not m:
        return None, None
    val = float(m.group(1))
    unit = _guess_unit_from_amount(s)
    return val, unit


def _guess_unit_from_amount(s: str) -> Optional[str]:
    if "кг" in s:
        return "кг"
    if "г" in s:
        return "г"
    if "мл" in s:
        return "мл"
    if re.search(r"\\bл\\b", s):
        return "л"
    if "шт" in s:
        return "шт"
    return None


def _extract_pack_count(name: str) -> Optional[int]:
    """
    Пытаемся вытащить количество в упаковке из названия товара.
    Примеры: '10шт', '10 шт', '12шт'
    """
    s = _norm(name).replace(" ", "")
    m = re.search(r"(\\d{1,3})шт", s)
    return int(m.group(1)) if m else None


@dataclass
class MatchResult:
    product: Dict[str, Any]
    score: float


def _best_match(ingredient_name: str, products: List[Dict[str, Any]]) -> Optional[MatchResult]:
    """
    Нечёткий матчинг:
    1) словарь синонимов (частичное совпадение)
    2) иначе similarity по нормализованным строкам
    """
    ing_n = _norm(ingredient_name)
    if not ing_n:
        return None

    # Синонимы
    synonyms = []
    for k, arr in INGREDIENT_MAPPING.items():
        if k in ing_n:
            synonyms = arr
            break

    best: Optional[MatchResult] = None
    for p in products:
        pn = _norm(p.get("name", ""))
        if not pn:
            continue

        # быстрый фильтр по синонимам
        if synonyms and not any(_norm(s) in pn for s in synonyms):
            continue

        score = _sim(ing_n, pn)
        # бонус за подстроку
        if ing_n in pn or pn in ing_n:
            score += 0.15
        if best is None or score > best.score:
            best = MatchResult(product=p, score=score)

    # порог
    if best and best.score >= 0.45:
        return best
    return None


def _calc_price_for_amount(product_price: float, product_name: str, product_unit: str, amount: str) -> Optional[int]:
    """
    Пытаемся получить цену под порцию:
    - если товар по кг, а amount в граммах/кг — масштабируем
    - если товар шт, а amount в штуках — масштабируем
    - если в названии есть '10шт' и amount меньше — делим на pack_count
    Возвращаем округлённую цену в рублях (int).
    """
    if product_price is None:
        return None

    val, unit = _parse_amount(amount)
    if val is None or unit is None:
        return int(round(product_price))

    product_unit = (product_unit or "шт").lower()

    # яйца/упаковки: '10шт'
    pack = _extract_pack_count(product_name)
    if pack and unit == "шт" and product_unit == "шт":
        per_one = product_price / pack
        return int(round(per_one * val))

    if product_unit == "кг":
        if unit == "г":
            return int(round(product_price * (val / 1000.0)))
        if unit == "кг":
            return int(round(product_price * val))

    if product_unit == "шт":
        if unit == "шт":
            return int(round(product_price * val))

    # fallback
    return int(round(product_price))


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        print(f"❌ Файл не найден: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Ошибка чтения {path}: {e}")
        return None


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    print("🔗 Начинаем маппинг ингредиентов...")

    recipes = load_json(RECIPES_FILE)
    if not recipes:
        return 0

    grocery = load_json(GROCERY_FILE)
    if not grocery:
        print("⚠️ grocery_prices.json недоступен — пропускаем обновление цен.")
        return 0

    products = grocery.get("products", []) or []
    if not products:
        print("⚠️ В grocery_prices.json нет товаров — пропускаем обновление цен.")
        return 0

    updated = 0
    total_ingredients = 0
    now = datetime.now().strftime("%Y-%m-%d")

    for recipe_key, recipe_data in recipes.items():
        total_price = 0
        for ing in recipe_data.get("ingredients", []):
            total_ingredients += 1
            ing_name = ing.get("name", "")
            match = _best_match(ing_name, products)

            if not match:
                print(f"⚠️ {ing_name} -> Не найдено в акциях")
                total_price += int(ing.get("price", 0) or 0)
                continue

            p = match.product
            new_price = _calc_price_for_amount(
                product_price=float(p.get("price", 0) or 0),
                product_name=p.get("name", ""),
                product_unit=p.get("unit", "шт"),
                amount=ing.get("amount", ""),
            )

            if new_price is None:
                print(f"⚠️ {ing_name} -> найдено, но цену рассчитать не удалось")
                total_price += int(ing.get("price", 0) or 0)
                continue

            old_price = int(ing.get("price", 0) or 0)

            # история
            ing.setdefault("price_history", [])
            ing["price_history"].append({"date": now, "price": new_price, "source": "Пятёрочка (ProShoper)"})
            ing["price_history"] = ing["price_history"][-12:]

            ing["price"] = new_price
            ing["last_updated"] = now
            ing["source"] = "Пятёрочка (ProShoper)"
            ing["matched_product"] = p.get("name")

            updated += 1
            total_price += new_price
            print(f"✅ {ing_name} -> {p.get('name')} ({new_price}₽)")

        recipe_data["total_price"] = total_price
        recipe_data["last_updated"] = now

    # сохраняем
    save_json(RECIPES_FILE, recipes)
    percent = (updated / total_ingredients * 100.0) if total_ingredients else 0.0
    print(f"📊 Обновлено: {updated}/{total_ingredients} ингредиентов ({percent:.0f}%)")
    print("💾 Сохранено в recipes_prices.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


