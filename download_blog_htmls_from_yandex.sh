#!/bin/bash
# Скрипт для скачивания HTML файлов блога из Yandex Cloud

set -e

BUCKET_NAME="www.tabatatimer.ru"
ENDPOINT_URL="https://storage.yandexcloud.net"
BLOG_DIR="../public_html/blog"

# Проверяем наличие AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI не установлен. Устанавливаю..."
    pip install awscli
fi

# Проверяем переменные окружения
if [ -z "$YANDEX_ACCESS_KEY_ID" ] || [ -z "$YANDEX_SECRET_ACCESS_KEY" ]; then
    echo "⚠️ Переменные окружения YANDEX_ACCESS_KEY_ID и YANDEX_SECRET_ACCESS_KEY не установлены"
    echo "Используем значения из GitHub Secrets (для GitHub Actions) или .env файла"
    
    # Пробуем загрузить из .env если существует
    if [ -f .env ]; then
        source .env
    fi
fi

# Создаём директорию если не существует
mkdir -p "$BLOG_DIR"

echo "📥 Скачиваю HTML файлы из Yandex Cloud..."
echo "Bucket: $BUCKET_NAME"
echo "Path: blog/"

# Настраиваем AWS CLI для Yandex Cloud
export AWS_ACCESS_KEY_ID="${YANDEX_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${YANDEX_SECRET_ACCESS_KEY}"
export AWS_DEFAULT_REGION="ru-central1"

# Скачиваем все HTML файлы из папки blog/
aws s3 sync "s3://${BUCKET_NAME}/blog/" "$BLOG_DIR/" \
    --endpoint-url="$ENDPOINT_URL" \
    --exclude "*" \
    --include "*.html" \
    --no-progress

if [ $? -eq 0 ]; then
    echo "✅ HTML файлы успешно скачаны в $BLOG_DIR"
    ls -lh "$BLOG_DIR"/*.html | awk '{print $9, $5}'
else
    echo "❌ Ошибка при скачивании файлов"
    exit 1
fi
