#!/bin/bash

# Скрипт для установки публичного ACL для всех файлов в S3-бакете VK Cloud

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BUCKET_NAME="tabatatimer"
ENDPOINT_URL="https://hb.ru-msk.vkcloud-storage.ru"
PROFILE_NAME="vkcloud-old"

echo -e "${GREEN}🚀 Установка публичного ACL для всех файлов в бакете${NC}"
echo ""

# Получаем список всех объектов
echo -e "${YELLOW}📋 Получение списка всех объектов...${NC}"
OBJECTS=$(aws s3 ls s3://$BUCKET_NAME/ --recursive --endpoint-url "$ENDPOINT_URL" --profile "$PROFILE_NAME" | awk '{print $4}')

TOTAL=$(echo "$OBJECTS" | grep -v "^$" | wc -l | tr -d ' ')
echo -e "${GREEN}✅ Найдено объектов: $TOTAL${NC}"
echo ""

if [ "$TOTAL" -eq 0 ]; then
    echo -e "${RED}❌ Объекты не найдены${NC}"
    exit 1
fi

# Устанавливаем ACL для каждого объекта
echo -e "${YELLOW}🔧 Установка публичного ACL...${NC}"
echo ""

COUNT=0
ERRORS=0

while IFS= read -r object; do
    if [ -z "$object" ]; then
        continue
    fi
    
    COUNT=$((COUNT + 1))
    
    # Показываем прогресс каждые 10 файлов
    if [ $((COUNT % 10)) -eq 0 ]; then
        echo -e "${YELLOW}  Обработано: $COUNT / $TOTAL${NC}"
    fi
    
    # Устанавливаем ACL
    if aws s3api put-object-acl \
        --bucket "$BUCKET_NAME" \
        --key "$object" \
        --acl public-read \
        --endpoint-url "$ENDPOINT_URL" \
        --profile "$PROFILE_NAME" 2>/dev/null; then
        : # Успешно
    else
        ERRORS=$((ERRORS + 1))
        echo -e "${RED}  ⚠️  Ошибка для: $object${NC}"
    fi
done <<< "$OBJECTS"

echo ""
echo -e "${GREEN}✅ Обработка завершена!${NC}"
echo "  Успешно: $((TOTAL - ERRORS))"
echo "  Ошибок: $ERRORS"
echo ""

# Проверка доступа
echo -e "${YELLOW}🔍 Проверка публичного доступа...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${BUCKET_NAME}.hb.ru-msk.vkcloud-storage.ru/index.html" || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Публичный доступ работает! (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo "Сайт доступен по адресу:"
    echo "  https://${BUCKET_NAME}.hb.ru-msk.vkcloud-storage.ru"
else
    echo -e "${YELLOW}⚠️  Доступ: HTTP $HTTP_CODE${NC}"
fi

