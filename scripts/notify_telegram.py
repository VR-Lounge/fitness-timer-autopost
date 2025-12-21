#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для отправки уведомления в Telegram о парсинге цен
"""

import os
import json
import requests

def send_telegram_notification():
    """Отправляет уведомление в Telegram о результатах парсинга цен"""
    
    # Получение токена и chat_id из переменных окружения
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ Ошибка: не указаны TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return
    
    # Чтение данных из файла grocery_prices.json
    try:
        with open('grocery_prices.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Файл grocery_prices.json не найден")
        return
    except json.JSONDecodeError:
        print("❌ Ошибка чтения JSON из grocery_prices.json")
        return
    
    # Формирование сообщения
    count = len(data.get('products', []))
    date = data.get('last_updated', 'неизвестно')
    
    message = (
        "📊 Цены обновлены!\n\n"
        f"🏪 Источник: Пятёрочка (ProShoper)\n"
        f"📅 Дата: {date}\n"
        f"✅ Товаров спарсено: {count}"
    )
    
    # Отправка сообщения в Telegram
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Уведомление успешно отправлено в Telegram")
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")

if __name__ == '__main__':
    send_telegram_notification()
