#!/bin/bash

# Скрипт для ручной загрузки файлов блога на Яндекс Cloud Object Storage
# Использование: 
#   export YANDEX_ACCESS_KEY_ID="ваш_ключ"
#   export YANDEX_SECRET_ACCESS_KEY="ваш_секрет"
#   bash upload_to_yandex_manual.sh

set -e

BUCKET_NAME="www.tabatatimer.ru"
ENDPOINT_URL="https://storage.yandexcloud.net"

# Определяем путь к public_html
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/../public_html" ]; then
    SOURCE_DIR="$SCRIPT_DIR/../public_html"
elif [ -d "../public_html" ]; then
    SOURCE_DIR="../public_html"
elif [ -d "public_html" ]; then
    SOURCE_DIR="public_html"
else
    echo "❌ Папка public_html не найдена"
    exit 1
fi

# Проверка наличия AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI не установлен"
    echo "Установите: brew install awscli (macOS) или apt-get install awscli (Linux)"
    exit 1
fi

# Проверка переменных окружения для Яндекс Cloud
if [ -z "$YANDEX_ACCESS_KEY_ID" ] || [ -z "$YANDEX_SECRET_ACCESS_KEY" ]; then
    echo "❌ Переменные окружения YANDEX_ACCESS_KEY_ID и YANDEX_SECRET_ACCESS_KEY не установлены"
    echo ""
    echo "Установите их перед запуском:"
    echo "  export YANDEX_ACCESS_KEY_ID='ваш_ключ'"
    echo "  export YANDEX_SECRET_ACCESS_KEY='ваш_секрет'"
    echo ""
    echo "Или получите из GitHub Secrets:"
    echo "  https://github.com/VR-Lounge/fitness-timer-autopost/settings/secrets/actions"
    exit 1
fi

# Настройка AWS CLI для Яндекс Cloud
export AWS_ACCESS_KEY_ID="$YANDEX_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$YANDEX_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="ru-central1"

echo "📤 Загрузка файлов блога на Яндекс Cloud..."
echo "   Bucket: $BUCKET_NAME"
echo "   Source: $SOURCE_DIR"
echo ""

cd "$SOURCE_DIR"

# Загружаем blog-posts.json
if [ -f "blog-posts.json" ]; then
    echo "📄 Загружаю blog-posts.json..."
    aws s3 cp blog-posts.json "s3://$BUCKET_NAME/blog-posts.json" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read
    echo "✅ blog-posts.json загружен"
    echo ""
fi

# Загружаем blog.html
if [ -f "blog.html" ]; then
    echo "📄 Загружаю blog.html..."
    aws s3 cp blog.html "s3://$BUCKET_NAME/blog.html" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read
    echo "✅ blog.html загружен"
    echo ""
fi

# Загружаем все HTML страницы статей из папки blog/
if [ -d "blog" ]; then
    echo "📄 Загружаю HTML страницы статей..."
    aws s3 sync blog/ "s3://$BUCKET_NAME/blog/" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read \
        --exclude "*.DS_Store" \
        --delete
    echo "✅ HTML страницы статей загружены"
    echo ""
fi

# Загружаем обновлённый sitemap.xml
if [ -f "sitemap.xml" ]; then
    echo "📄 Загружаю sitemap.xml..."
    aws s3 cp sitemap.xml "s3://$BUCKET_NAME/sitemap.xml" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read
    echo "✅ sitemap.xml загружен"
    echo ""
fi

# Загружаем обновлённый robots.txt
if [ -f "robots.txt" ]; then
    echo "📄 Загружаю robots.txt..."
    aws s3 cp robots.txt "s3://$BUCKET_NAME/robots.txt" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read
    echo "✅ robots.txt загружен"
    echo ""
fi

# Загружаем изображения блога
if [ -d "images/blog" ]; then
    echo "🖼️  Загружаю изображения блога..."
    aws s3 sync images/blog/ "s3://$BUCKET_NAME/images/blog/" \
        --endpoint-url="$ENDPOINT_URL" \
        --acl public-read \
        --exclude "*.DS_Store"
    echo "✅ Изображения блога загружены"
    echo ""
fi

echo "✅ Все файлы блога загружены на Яндекс Cloud!"
echo ""
echo "🌐 Проверьте сайт: https://www.tabatatimer.ru/blog.html"
