#!/bin/bash

# Скрипт для настройки AWS CLI для работы с Yandex Cloud Object Storage

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PROFILE_NAME="yandex"

echo -e "${BLUE}🔧 Настройка AWS CLI для Yandex Cloud${NC}"
echo ""
echo -e "${YELLOW}📋 Инструкция:${NC}"
echo "1. Перейдите в консоль Yandex Cloud: https://console.yandex.cloud/"
echo "2. Выберите каталог (например: cloud-admintabatatimerru или default)"
echo "3. Перейдите в раздел 'Сервисные аккаунты' (Service Accounts)"
echo "4. Создайте новый сервисный аккаунт или используйте существующий"
echo "5. Создайте статический ключ доступа (Access Key)"
echo "6. Скопируйте Access Key ID и Secret Access Key"
echo ""

read -p "Введите Access Key ID: " ACCESS_KEY_ID
read -sp "Введите Secret Access Key: " SECRET_ACCESS_KEY
echo ""

if [ -z "$ACCESS_KEY_ID" ] || [ -z "$SECRET_ACCESS_KEY" ]; then
    echo -e "${RED}❌ Ключи доступа не могут быть пустыми${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}🔧 Настройка профиля...${NC}"

# Настройка профиля
aws configure set aws_access_key_id "$ACCESS_KEY_ID" --profile "$PROFILE_NAME"
aws configure set aws_secret_access_key "$SECRET_ACCESS_KEY" --profile "$PROFILE_NAME"
aws configure set region ru-central1 --profile "$PROFILE_NAME"
aws configure set output json --profile "$PROFILE_NAME"

echo ""
echo -e "${GREEN}✅ Профиль '$PROFILE_NAME' успешно настроен!${NC}"
echo ""

# Проверка подключения
echo -e "${YELLOW}🔍 Проверка подключения к Yandex Cloud...${NC}"
if aws s3 ls --endpoint-url=https://storage.yandexcloud.net --profile "$PROFILE_NAME" 2>&1 | grep -q "www.tabatatimer.ru"; then
    echo -e "${GREEN}✅ Подключение успешно! Бакет найден.${NC}"
else
    echo -e "${YELLOW}⚠️  Бакет 'www.tabatatimer.ru' не найден в списке${NC}"
    echo "   Это нормально, если бакет только что создан"
    echo "   Попробуйте проверить вручную:"
    echo "   aws s3 ls --endpoint-url=https://storage.yandexcloud.net --profile $PROFILE_NAME"
fi

echo ""
echo -e "${GREEN}🎉 Настройка завершена!${NC}"
echo ""
echo "Теперь вы можете загрузить файлы командой:"
echo "  ./upload_to_yandex_cloud.sh"

