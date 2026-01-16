#!/bin/bash

# Скрипт для настройки публичного доступа к S3-бакету VK Cloud
# Использование: ./setup_vkcloud_s3.sh YOUR_SECRET_KEY

set -e  # Остановка при ошибке

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Настройка публичного доступа к S3-бакету VK Cloud${NC}"
echo ""

# Проверка наличия Secret Key
if [ -z "$1" ]; then
    echo -e "${RED}❌ Ошибка: Не указан Secret Key${NC}"
    echo ""
    echo "Использование:"
    echo "  ./setup_vkcloud_s3.sh YOUR_SECRET_KEY"
    echo ""
    echo "Пример:"
    echo "  ./setup_vkcloud_s3.sh aMXfZHdGV9PtF7uHQo5dJ6k5EgE2SHE3XcUTujtzQYeK"
    exit 1
fi

SECRET_KEY="$1"
ACCESS_KEY_ID="5QFbmJmX45AzvRGs3gzwDD"
BUCKET_NAME="tabatatimer"
ENDPOINT_URL="https://hb.ru-msk.vkcloud-storage.ru"
PROFILE_NAME="vkcloud"

echo -e "${YELLOW}📋 Параметры:${NC}"
echo "  Access Key ID: $ACCESS_KEY_ID"
echo "  Bucket: $BUCKET_NAME"
echo "  Endpoint: $ENDPOINT_URL"
echo ""

# Проверка установки AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI не установлен${NC}"
    echo ""
    echo "Установите AWS CLI:"
    echo "  brew install awscli"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI установлен${NC}"
echo ""

# Настройка credentials
echo -e "${YELLOW}🔑 Настройка credentials...${NC}"
aws configure set aws_access_key_id "$ACCESS_KEY_ID" --profile "$PROFILE_NAME"
aws configure set aws_secret_access_key "$SECRET_KEY" --profile "$PROFILE_NAME"
aws configure set region ru-msk --profile "$PROFILE_NAME"

echo -e "${GREEN}✅ Credentials настроены${NC}"
echo ""

# Создание bucket-policy.json
echo -e "${YELLOW}📝 Создание bucket-policy.json...${NC}"
POLICY_FILE="/tmp/bucket-policy.json"

cat > "$POLICY_FILE" << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::tabatatimer/*"
    }
  ]
}
EOF

echo -e "${GREEN}✅ Файл bucket-policy.json создан${NC}"
echo ""

# Применение bucket policy
echo -e "${YELLOW}🔧 Применение bucket policy...${NC}"
aws s3api put-bucket-policy \
  --bucket "$BUCKET_NAME" \
  --policy "file://$POLICY_FILE" \
  --endpoint-url "$ENDPOINT_URL" \
  --profile "$PROFILE_NAME"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Bucket policy успешно применена!${NC}"
else
    echo -e "${RED}❌ Ошибка при применении bucket policy${NC}"
    exit 1
fi

echo ""

# Проверка доступа
echo -e "${YELLOW}🔍 Проверка публичного доступа...${NC}"
TEST_URL="https://${BUCKET_NAME}.hb.ru-msk.vkcloud-storage.ru/index.html"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$TEST_URL" || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Публичный доступ работает! (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo -e "${GREEN}🎉 Настройка завершена успешно!${NC}"
    echo ""
    echo "Теперь сайт доступен по адресу:"
    echo "  https://${BUCKET_NAME}.hb.ru-msk.vkcloud-storage.ru"
elif [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "000" ]; then
    echo -e "${YELLOW}⚠️  Доступ пока не работает (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo "Возможные причины:"
    echo "  1. Bucket policy применена, но нужно подождать несколько минут"
    echo "  2. Проверьте настройки CORS в панели VK Cloud"
    echo "  3. Убедитесь, что бакет существует и содержит файлы"
else
    echo -e "${YELLOW}⚠️  Неожиданный ответ (HTTP $HTTP_CODE)${NC}"
fi

echo ""
echo -e "${GREEN}📋 Дополнительные команды:${NC}"
echo ""
echo "Проверка bucket policy:"
echo "  aws s3api get-bucket-policy --bucket $BUCKET_NAME --endpoint-url $ENDPOINT_URL --profile $PROFILE_NAME"
echo ""
echo "Список файлов в бакете:"
echo "  aws s3 ls s3://$BUCKET_NAME/ --endpoint-url $ENDPOINT_URL --profile $PROFILE_NAME"
echo ""
echo "Загрузка файла:"
echo "  aws s3 cp file.txt s3://$BUCKET_NAME/ --endpoint-url $ENDPOINT_URL --profile $PROFILE_NAME"

