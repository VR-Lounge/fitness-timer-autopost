#!/bin/bash

# Скрипт для загрузки файлов сайта tabatatimer.ru в Yandex Cloud Object Storage

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

BUCKET_NAME="www.tabatatimer.ru"
ENDPOINT_URL="https://storage.yandexcloud.net"
PROFILE_NAME="yandex"
SOURCE_DIR="/Users/LOBANOFF-PRO/Documents/TABATATIMER.RU/С MediaPipe/public_html"

echo -e "${BLUE}🚀 Загрузка файлов сайта в Yandex Cloud Object Storage${NC}"
echo ""
echo -e "${YELLOW}📋 Параметры:${NC}"
echo "  Бакет: $BUCKET_NAME"
echo "  Endpoint: $ENDPOINT_URL"
echo "  Профиль: $PROFILE_NAME"
echo "  Источник: $SOURCE_DIR"
echo ""

# Проверка наличия AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI не установлен${NC}"
    echo "Установите через: brew install awscli"
    exit 1
fi

# Проверка настройки профиля
echo -e "${YELLOW}🔍 Проверка настройки профиля AWS CLI...${NC}"
if ! aws configure list --profile "$PROFILE_NAME" &> /dev/null || [ -z "$(aws configure get aws_access_key_id --profile "$PROFILE_NAME" 2>/dev/null)" ]; then
    echo -e "${RED}❌ Профиль '$PROFILE_NAME' не настроен${NC}"
    echo ""
    echo -e "${YELLOW}📝 Настройте профиль командой:${NC}"
    echo "  aws configure --profile yandex"
    echo ""
    echo "Введите следующие данные:"
    echo "  AWS Access Key ID: [ваш Access Key ID из Yandex Cloud]"
    echo "  AWS Secret Access Key: [ваш Secret Access Key из Yandex Cloud]"
    echo "  Default region name: ru-central1"
    echo "  Default output format: json"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Профиль настроен${NC}"
echo ""

# Проверка существования исходной директории
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}❌ Исходная директория не найдена: $SOURCE_DIR${NC}"
    exit 1
fi

# Подсчет файлов
echo -e "${YELLOW}📊 Подсчет файлов для загрузки...${NC}"
FILE_COUNT=$(find "$SOURCE_DIR" -type f | wc -l | tr -d ' ')
SIZE=$(du -sh "$SOURCE_DIR" | awk '{print $1}')
echo -e "${GREEN}✅ Найдено файлов: $FILE_COUNT (размер: $SIZE)${NC}"
echo ""

# Проверка наличия index.html
if [ ! -f "$SOURCE_DIR/index.html" ]; then
    echo -e "${RED}❌ Файл index.html не найден в исходной директории${NC}"
    exit 1
fi

echo -e "${GREEN}✅ index.html найден${NC}"
echo ""

# Подтверждение
echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Все файлы в бакете будут заменены!${NC}"
echo ""
read -p "Продолжить загрузку? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}❌ Загрузка отменена${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}📤 Начало загрузки файлов...${NC}"
echo ""

# Загрузка файлов
cd "$SOURCE_DIR"

START_TIME=$(date +%s)

echo -e "${YELLOW}📤 Загрузка файлов (это может занять несколько минут)...${NC}"
echo ""

aws s3 sync . "s3://$BUCKET_NAME" \
  --endpoint-url="$ENDPOINT_URL" \
  --profile "$PROFILE_NAME" \
  --acl public-read \
  --exclude ".git/*" \
  --exclude ".DS_Store" \
  --exclude "*.log" \
  --exclude ".gitignore" \
  --exclude "node_modules/*" \
  --exclude ".env" \
  --exclude ".env.*" \
  --delete

EXIT_CODE=$?

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Загрузка завершена успешно!${NC}"
    echo "  Время загрузки: ${DURATION} секунд"
    echo ""
    echo -e "${YELLOW}🔍 Проверка результата:${NC}"
    echo "  1. Проверьте в консоли Yandex Cloud:"
    echo "     https://console.yandex.cloud/folders/b1gmsesnb2h7cs5c7qov/storage/buckets/$BUCKET_NAME"
    echo ""
    echo "  2. Проверьте прямой URL:"
    echo "     http://$BUCKET_NAME.website.yandexcloud.net"
    echo ""
    echo "  3. После распространения DNS (1-2 часа):"
    echo "     https://www.tabatatimer.ru"
else
    echo -e "${RED}❌ Ошибка при загрузке (код: $EXIT_CODE)${NC}"
    exit $EXIT_CODE
fi

