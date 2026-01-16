#!/bin/bash
# Скрипт для развёртывания на Yandex Cloud
# Использование: ./deploy_to_yandex_cloud.sh

set -e

echo "🚀 Развёртывание системы автоответов на Yandex Cloud"
echo "=================================================="

# Проверка наличия Yandex Cloud CLI
if ! command -v yc &> /dev/null; then
    echo "❌ Yandex Cloud CLI не установлен!"
    echo "📖 Установите: https://cloud.yandex.ru/docs/cli/quickstart"
    exit 1
fi

echo "✅ Yandex Cloud CLI найден"

# Проверка авторизации
if ! yc config list &> /dev/null; then
    echo "❌ Не авторизованы в Yandex Cloud!"
    echo "📖 Выполните: yc init"
    exit 1
fi

echo "✅ Авторизация проверена"

# Создание ZIP архива
echo ""
echo "📦 Создание архива с кодом..."
zip -r telegram-auto-reply.zip \
    auto_reply.py \
    statistics.py \
    requirements.txt \
    -x "*.pyc" "__pycache__/*" "*.log" ".env" \
    "*.json" "*.md" "*.sh" ".git/*"

echo "✅ Архив создан: telegram-auto-reply.zip"

# Запрос переменных окружения
echo ""
echo "📝 Настройка переменных окружения..."
echo ""

read -p "DEEPSEEK_API_KEY: " DEEPSEEK_API_KEY
ADMIN_TELEGRAM_CHAT_ID="422372115"  # @lobanoff_pro
echo "✅ ADMIN_TELEGRAM_CHAT_ID настроен: $ADMIN_TELEGRAM_CHAT_ID (@lobanoff_pro)"

# Готовые значения
TELEGRAM_BOT_TOKEN="8228469773:AAF2_m6lyWDp4nqaIh7glXqd7PQ6uycXPfo"
TELEGRAM_CHAT_ID="-1003382880193"
SMTP_SERVER="smtp.yandex.ru"
SMTP_PORT="465"
SMTP_USER="admin@tabatatimer.ru"
SMTP_PASSWORD="thyspickpikpnqdq"

# Создание функции
echo ""
echo "🔧 Создание Cloud Function..."
yc serverless function create --name telegram-auto-reply 2>/dev/null || echo "Функция уже существует"

# Создание версии функции
echo ""
echo "📤 Загрузка кода..."
yc serverless function version create \
  --function-name telegram-auto-reply \
  --runtime python311 \
  --entrypoint auto_reply.главная \
  --memory 256m \
  --execution-timeout 60s \
  --source-path telegram-auto-reply.zip \
  --environment \
    TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN",\
    TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID",\
    DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY",\
    ADMIN_TELEGRAM_CHAT_ID="$ADMIN_TELEGRAM_CHAT_ID",\
    SMTP_SERVER="$SMTP_SERVER",\
    SMTP_PORT="$SMTP_PORT",\
    SMTP_USER="$SMTP_USER",\
    SMTP_PASSWORD="$SMTP_PASSWORD"

echo ""
echo "✅ Функция создана и загружена!"

# Создание триггера (каждые 30 минут)
echo ""
echo "⏰ Настройка триггера (каждые 30 минут)..."
yc serverless trigger create timer \
  --function-name telegram-auto-reply \
  --cron-expression "*/30 * * * *" \
  2>/dev/null || echo "Триггер уже существует"

echo ""
echo "✅ Триггер настроен!"

# Очистка
rm -f telegram-auto-reply.zip

echo ""
echo "🎉 Развёртывание завершено!"
echo ""
echo "📊 Проверка логов:"
echo "   yc serverless function logs telegram-auto-reply --tail"
echo ""
echo "🧪 Тестовый запуск:"
echo "   yc serverless function invoke telegram-auto-reply"

