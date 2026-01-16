#!/bin/bash

# Скрипт для загрузки файлов блога на Яндекс Cloud Object Storage
# Используется в GitHub Actions после генерации постов

set -e

BUCKET_NAME="www.tabatatimer.ru"
ENDPOINT_URL="https://storage.yandexcloud.net"

# Определяем путь к public_html
# В GitHub Actions репозиторий клонируется в fitness-timer-autopost, а public_html - отдельно
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# В GitHub Actions структура: fitness-timer-autopost/ и public_html/ на одном уровне
if [ -d "$(dirname "$SCRIPT_DIR")/../public_html" ]; then
    # Мы в fitness-timer-autopost, public_html на уровень выше (в родительской директории)
    SOURCE_DIR="$(dirname "$SCRIPT_DIR")/../public_html"
elif [ -d "$SCRIPT_DIR/../public_html" ]; then
    # Мы в fitness-timer-autopost, public_html на уровень выше
    SOURCE_DIR="$SCRIPT_DIR/../public_html"
elif [ -d "../public_html" ]; then
    # public_html на уровень выше от текущей директории
    SOURCE_DIR="../public_html"
elif [ -d "public_html" ]; then
    # public_html в текущей директории
    SOURCE_DIR="public_html"
else
    echo "❌ Папка public_html не найдена"
    echo "Проверяю текущую директорию: $(pwd)"
    echo "Проверяю структуру:"
    ls -la .. | head -10
    exit 1
fi

# Проверка наличия AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI не установлен"
    exit 1
fi

# Проверка переменных окружения для Яндекс Cloud
if [ -z "$YANDEX_ACCESS_KEY_ID" ] || [ -z "$YANDEX_SECRET_ACCESS_KEY" ]; then
    echo "⚠️ Переменные окружения YANDEX_ACCESS_KEY_ID и YANDEX_SECRET_ACCESS_KEY не установлены"
    echo "Пропускаем загрузку на Яндекс Cloud"
    exit 0
fi

# Настройка AWS CLI для Яндекс Cloud
export AWS_ACCESS_KEY_ID="$YANDEX_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$YANDEX_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="ru-central1"

echo "📤 Загрузка файлов блога на Яндекс Cloud..."

# Загружаем только файлы блога
cd "$SOURCE_DIR"

# Загружаем blog-posts.json
if [ -f "blog-posts.json" ]; then
    aws s3 cp blog-posts.json "s3://$BUCKET_NAME/blog-posts.json" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read
    echo "✅ blog-posts.json загружен"
fi

# Загружаем blog.html
if [ -f "blog.html" ]; then
    aws s3 cp blog.html "s3://$BUCKET_NAME/blog.html" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read
    echo "✅ blog.html загружен"
fi

# Загружаем все HTML страницы статей из папки blog/
if [ -d "blog" ]; then
    aws s3 sync blog/ "s3://$BUCKET_NAME/blog/" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read \
        --exclude "*.DS_Store"
    echo "✅ HTML страницы статей загружены"
fi

# Загружаем обновлённый sitemap.xml
if [ -f "sitemap.xml" ]; then
    aws s3 cp sitemap.xml "s3://$BUCKET_NAME/sitemap.xml" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read
    echo "✅ sitemap.xml загружен"
fi

# Загружаем обновлённый robots.txt
if [ -f "robots.txt" ]; then
    aws s3 cp robots.txt "s3://$BUCKET_NAME/robots.txt" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read
    echo "✅ robots.txt загружен"
fi

# Загружаем изображения блога
if [ -d "images/blog" ]; then
    aws s3 sync images/blog/ "s3://$BUCKET_NAME/images/blog/" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read \
        --exclude "*.DS_Store"
    echo "✅ Изображения блога загружены"
fi

echo "✅ Все файлы блога загружены на Яндекс Cloud!"
