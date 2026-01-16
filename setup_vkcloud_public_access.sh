#!/bin/bash

# Скрипт для настройки публичного доступа к объектам в S3-бакете VK Cloud
# VK Cloud не поддерживает PutBucketPolicy, поэтому используем публичный ACL для объектов

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Настройка публичного доступа к объектам в S3-бакете VK Cloud${NC}"
echo ""

ACCESS_KEY_ID="wBawWbvmfgJHD5Uv2ZkbEQ"
SECRET_KEY="aMXfZHdGV9PtF7uHQo5dJ6k5EgE2SHE3XcUTujtzQYeK"
BUCKET_NAME="tabatatimer"
ENDPOINT_URL="https://hb.ru-msk.vkcloud-storage.ru"
PROFILE_NAME="vkcloud-old"

# Настройка credentials
echo -e "${YELLOW}🔑 Настройка credentials...${NC}"
aws configure set aws_access_key_id "$ACCESS_KEY_ID" --profile "$PROFILE_NAME"
aws configure set aws_secret_access_key "$SECRET_KEY" --profile "$PROFILE_NAME"
aws configure set region ru-msk --profile "$PROFILE_NAME"

echo -e "${GREEN}✅ Credentials настроены${NC}"
echo ""

# Проверка существования бакета
echo -e "${YELLOW}🔍 Проверка бакета...${NC}"
if aws s3api head-bucket --bucket "$BUCKET_NAME" --endpoint-url "$ENDPOINT_URL" --profile "$PROFILE_NAME" 2>/dev/null; then
    echo -e "${GREEN}✅ Бакет найден${NC}"
else
    echo -e "${RED}❌ Бакет не найден${NC}"
    exit 1
fi

echo ""

# ВАЖНО: VK Cloud не поддерживает PutBucketPolicy через API
echo -e "${YELLOW}⚠️  ВАЖНО: VK Cloud не поддерживает PutBucketPolicy через API${NC}"
echo ""
echo "Для настройки публичного доступа нужно:"
echo ""
echo "1. 📱 Открой веб-интерфейс VK Cloud:"
echo "   https://mcs.mail.ru/app/services/object-storage/buckets"
echo ""
echo "2. 🔍 Найди бакет 'tabatatimer'"
echo ""
echo "3. ⚙️  Открой настройки бакета → 'Публичный доступ' или 'Public Access'"
echo ""
echo "4. ✅ Включи публичный доступ для чтения (Read)"
echo ""
echo "5. 💾 Сохрани изменения"
echo ""
echo "Альтернативно, можно использовать команды ниже для установки публичного ACL"
echo "для каждого объекта (но это долго для большого количества файлов):"
echo ""

# Функция для установки публичного ACL для объекта
set_public_acl() {
    local object_key="$1"
    echo "  Устанавливаю публичный ACL для: $object_key"
    aws s3api put-object-acl \
        --bucket "$BUCKET_NAME" \
        --key "$object_key" \
        --acl public-read \
        --endpoint-url "$ENDPOINT_URL" \
        --profile "$PROFILE_NAME" 2>/dev/null || echo "    ⚠️  Не удалось установить ACL (возможно, не поддерживается)"
}

# Получаем список всех объектов
echo -e "${YELLOW}📋 Получение списка объектов...${NC}"
OBJECTS=$(aws s3 ls s3://$BUCKET_NAME/ --recursive --endpoint-url "$ENDPOINT_URL" --profile "$PROFILE_NAME" | awk '{print $4}')

OBJECT_COUNT=$(echo "$OBJECTS" | wc -l | tr -d ' ')
echo -e "${GREEN}✅ Найдено объектов: $OBJECT_COUNT${NC}"
echo ""

# Спрашиваем, нужно ли устанавливать ACL для всех объектов
echo -e "${YELLOW}❓ Установить публичный ACL для всех объектов? (это может занять время)${NC}"
echo "   Нажми Enter для пропуска (рекомендуется настроить через веб-интерфейс)"
read -t 5 -r || true

if [ -z "$REPLY" ]; then
    echo ""
    echo -e "${YELLOW}⏭️  Пропускаем установку ACL для объектов${NC}"
    echo ""
    echo -e "${GREEN}📋 Следующие шаги:${NC}"
    echo ""
    echo "1. Открой веб-интерфейс VK Cloud"
    echo "2. Найди бакет 'tabatatimer'"
    echo "3. Включи публичный доступ в настройках"
    echo "4. Проверь доступ: curl https://tabatatimer.hb.ru-msk.vkcloud-storage.ru/index.html"
    exit 0
fi

# Устанавливаем ACL для критически важных файлов
echo ""
echo -e "${YELLOW}🔧 Установка публичного ACL для критически важных файлов...${NC}"

CRITICAL_FILES=(
    "index.html"
    "index.php"
    "CNAME"
    "favicon.ico"
)

for file in "${CRITICAL_FILES[@]}"; do
    set_public_acl "$file"
done

echo ""
echo -e "${GREEN}✅ Настройка завершена${NC}"
echo ""
echo -e "${YELLOW}🔍 Проверка доступа...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${BUCKET_NAME}.hb.ru-msk.vkcloud-storage.ru/index.html" || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Публичный доступ работает! (HTTP $HTTP_CODE)${NC}"
elif [ "$HTTP_CODE" = "403" ]; then
    echo -e "${YELLOW}⚠️  Доступ пока запрещён (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo "Нужно включить публичный доступ через веб-интерфейс VK Cloud"
else
    echo -e "${YELLOW}⚠️  Неожиданный ответ (HTTP $HTTP_CODE)${NC}"
fi

