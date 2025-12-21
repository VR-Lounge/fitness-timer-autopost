#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт обновления цен продуктов из Пятёрочки

Использует:
- pyaterochka-api для получения актуальных цен
- recipes_prices.json для хранения данных
- Telegram Bot API для уведомлений о значительных изменениях

Автор: VR-Lounge
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None
    print("⚠️  requests не установлен. Уведомления в Telegram будут отключены.")

# Импорт будет работать только если установлен pyaterochka-api
try:
    from pyaterochka_api import Pyaterochka

    PYATEROCHKA_AVAILABLE = True
except ImportError:
    PYATEROCHKA_AVAILABLE = False
    print("⚠️  pyaterochka-api не установлен. Работаем в тестовом режиме.")


def load_recipes_data():
    """Загрузка данных о рецептах и ценах"""
    recipes_file = Path("recipes_prices.json")

    if not recipes_file.exists():
        print("❌ Файл recipes_prices.json не найден!")
        return None

    with open(recipes_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_recipes_data(data):
    """Сохранение обновлённых данных"""
    with open("recipes_prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ Данные успешно сохранены в recipes_prices.json")


async def update_prices_from_pyaterochka(data):
    """
    Обновление цен через API Пятёрочки

    Returns:
        list: Список значительных изменений цен (>20%)
    """
    if not PYATEROCHKA_AVAILABLE:
        print("⚠️  Пропускаем обновление цен (API недоступен)")
        return []

    changes = []

    async with Pyaterochka(debug=False) as api:
        # Находим ближайший магазин (Москва, центр)
        try:
            await api.find_store(longitude=37.63156, latitude=55.73768)
            print("✅ Подключились к магазину Пятёрочка в Москве")
        except Exception as e:
            print(f"❌ Ошибка подключения к магазину: {e}")
            return []

        # Обновляем цены для каждого рецепта
        for recipe_key, recipe_data in data.items():
            print(f"\n📋 Обновление рецепта: {recipe_data.get('название', recipe_key)}")
            total_price = 0

            for ingredient in recipe_data.get("ingredients", []):
                # Пропускаем если нет PLU (ID товара)
                if not ingredient.get("plu"):
                    print(f"   ⏭️  Пропуск {ingredient.get('name')} (нет PLU)")
                    total_price += ingredient.get("price", 0) or 0
                    continue

                try:
                    # Получаем актуальную цену
                    product_info = await api.product_info(ingredient["plu"])
                    new_price = product_info["props"]["pageProps"]["props"]["productStore"]["price"]
                    old_price = ingredient.get("price", 0) or 0

                    # Добавляем в историю
                    if "price_history" not in ingredient:
                        ingredient["price_history"] = []

                    ingredient["price_history"].append(
                        {"date": datetime.now().strftime("%Y-%m-%d"), "price": new_price}
                    )

                    # Ограничиваем историю последними 12 неделями
                    ingredient["price_history"] = ingredient["price_history"][-12:]

                    # Обновляем текущую цену
                    ingredient["price"] = new_price
                    ingredient["last_updated"] = datetime.now().strftime("%Y-%m-%d")

                    total_price += new_price

                    # Проверяем значительное изменение (>20%)
                    if old_price > 0:
                        change_percent = abs(new_price - old_price) / old_price
                        if change_percent > 0.20:
                            changes.append(
                                {
                                    "recipe": recipe_data.get("название", recipe_key),
                                    "ingredient": ingredient.get("name"),
                                    "old_price": old_price,
                                    "new_price": new_price,
                                    "change_percent": round(change_percent * 100, 1),
                                }
                            )
                            print(f"   🚨 ЗНАЧИТЕЛЬНОЕ ИЗМЕНЕНИЕ: {ingredient.get('name')}")
                            print(
                                f"      Было: {old_price}₽ → Стало: {new_price}₽ ({change_percent*100:+.1f}%)"
                            )
                        else:
                            print(f"   ✅ {ingredient.get('name')}: {new_price}₽")

                except Exception as e:
                    print(
                        f"   ❌ Ошибка получения цены для {ingredient.get('name')} (PLU {ingredient.get('plu')}): {e}"
                    )
                    total_price += ingredient.get("price", 0) or 0

            # Обновляем общую стоимость рецепта
            recipe_data["total_price"] = total_price
            recipe_data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            print(f"   💰 Итого: {total_price}₽")

    return changes


def send_telegram_notification(changes):
    """
    Отправка уведомления в Telegram о значительных изменениях цен

    Args:
        changes (list): Список изменений цен
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("ADMIN_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

    if not REQUESTS_AVAILABLE:
        print("⚠️  requests недоступен — пропускаем отправку уведомления в Telegram.")
        return

    if not token or not chat_id:
        print("⚠️  Telegram токен или chat_id не настроены. Пропускаем уведомление.")
        return

    if not changes:
        print("✅ Значительных изменений цен не обнаружено")
        return

    # Формируем сообщение
    message = "🚨 <b>ЗНАЧИТЕЛЬНЫЕ ИЗМЕНЕНИЯ ЦЕН ПРОДУКТОВ</b>\n\n"

    for change in changes:
        emoji = "📈" if change["new_price"] >= change["old_price"] else "📉"
        message += f"{emoji} <b>{change['recipe']}</b>\n"
        message += f"   -  {change['ingredient']}\n"
        message += f"   -  Было: {change['old_price']} ₽\n"
        message += f"   -  Стало: {change['new_price']} ₽\n"
        message += f"   -  Изменение: <b>{change['change_percent']:+.1f}%</b>\n\n"

    message += f"\n📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )

        if response.ok:
            print(f"✅ Отправлено уведомление в Telegram о {len(changes)} изменениях")
        else:
            print(f"❌ Ошибка отправки в Telegram: {response.text}")

    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")


async def main():
    """Основная функция"""
    print("=" * 60)
    print("🛒 ОБНОВЛЕНИЕ ЦЕН ПРОДУКТОВ ИЗ ПЯТЁРОЧКИ")
    print("=" * 60)

    # Загружаем данные
    data = load_recipes_data()
    if not data:
        return

    print(f"\n📊 Загружено рецептов: {len(data)}")

    # Обновляем цены
    changes = await update_prices_from_pyaterochka(data)

    # Сохраняем обновлённые данные
    save_recipes_data(data)

    # Отправляем уведомление если есть значительные изменения
    if changes:
        send_telegram_notification(changes)

    print("\n" + "=" * 60)
    print("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


