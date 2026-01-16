#!/bin/bash

# Скрипт для установки публичного ACL для всех музыкальных файлов в S3-бакете VK Cloud

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BUCKET_NAME="tabatatimer"
ENDPOINT_URL="https://hb.ru-msk.vkcloud-storage.ru"
PROFILE_NAME="vkcloud-old"
MUSIC_PATH="assets/music"

echo -e "${GREEN}🎵 Установка публичного ACL для музыкальных файлов${NC}"
echo ""

# Получаем список всех MP3 файлов
echo -e "${YELLOW}📋 Получение списка музыкальных файлов...${NC}"
FILES=$(aws s3 ls s3://$BUCKET_NAME/$MUSIC_PATH/ --endpoint-url "$ENDPOINT_URL" --profile "$PROFILE_NAME" 2>&1 | awk '{for(i=4;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/ $//' | grep "\.mp3$" || true)

TOTAL=$(echo "$FILES" | grep -v "^$" | wc -l | tr -d ' ')
echo -e "${GREEN}✅ Найдено музыкальных файлов: $TOTAL${NC}"
echo ""

if [ "$TOTAL" -eq 0 ]; then
    echo -e "${RED}❌ Музыкальные файлы не найдены${NC}"
    exit 1
fi

# Устанавливаем ACL для каждого файла
echo -e "${YELLOW}🔧 Установка публичного ACL...${NC}"
echo ""

COUNT=0
SUCCESS=0
ERRORS=0

while IFS= read -r file; do
    if [ -z "$file" ]; then
        continue
    fi
    
    COUNT=$((COUNT + 1))
    
    # Показываем прогресс каждые 5 файлов
    if [ $((COUNT % 5)) -eq 0 ]; then
        echo -e "${YELLOW}  Обработано: $COUNT / $TOTAL${NC}"
    fi
    
    # Устанавливаем ACL
    if aws s3api put-object-acl \
        --bucket "$BUCKET_NAME" \
        --key "$MUSIC_PATH/$file" \
        --acl public-read \
        --endpoint-url "$ENDPOINT_URL" \
        --profile "$PROFILE_NAME" 2>/dev/null; then
        SUCCESS=$((SUCCESS + 1))
    else
        ERRORS=$((ERRORS + 1))
        echo -e "${RED}  ⚠️  Ошибка для: $file${NC}"
    fi
done <<< "$FILES"

echo ""
echo -e "${GREEN}✅ Обработка завершена!${NC}"
echo "  Успешно: $SUCCESS"
echo "  Ошибок: $ERRORS"
echo ""

# Проверка доступа
echo -e "${YELLOW}🔍 Проверка доступа к музыкальным файлам...${NC}"
TEST_FILES=("Tabata - Rocky.mp3" "Tabata - Eye Of The Tiger.mp3" "Tabata - Lose Yourself.mp3")

for file in "${TEST_FILES[@]}"; do
    ENCODED=$(echo "$file" | sed 's/ /%20/g')
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${BUCKET_NAME}.hb.ru-msk.vkcloud-storage.ru/$MUSIC_PATH/$ENCODED" || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ $file (HTTP $HTTP_CODE)${NC}"
    else
        echo -e "${YELLOW}⚠️  $file (HTTP $HTTP_CODE)${NC}"
    fi
done

