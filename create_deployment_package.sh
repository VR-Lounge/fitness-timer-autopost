#!/bin/bash
# Создание ZIP архива для развёртывания на Yandex Cloud
# Использование: ./create_deployment_package.sh

set -e

echo "📦 Создание пакета для развёртывания..."
echo "========================================"

# Имя архива
ARCHIVE_NAME="telegram-auto-reply.zip"

# Удаление старого архива, если есть
if [ -f "$ARCHIVE_NAME" ]; then
    echo "🗑️  Удаление старого архива..."
    rm -f "$ARCHIVE_NAME"
fi

# Создание временной директории
TEMP_DIR=$(mktemp -d)
echo "📁 Временная директория: $TEMP_DIR"

# Копирование необходимых файлов
echo "📋 Копирование файлов..."
cp auto_reply.py "$TEMP_DIR/"
cp statistics.py "$TEMP_DIR/"
cp requirements.txt "$TEMP_DIR/"

# Создание ZIP архива
echo "📦 Создание ZIP архива..."
cd "$TEMP_DIR"
zip -r "$ARCHIVE_NAME" . > /dev/null
mv "$ARCHIVE_NAME" "$OLDPWD/"

# Очистка
cd "$OLDPWD"
rm -rf "$TEMP_DIR"

echo ""
echo "✅ Архив создан: $ARCHIVE_NAME"
echo ""
echo "📊 Содержимое архива:"
unzip -l "$ARCHIVE_NAME" | grep -E "\.(py|txt)$"
echo ""
echo "🚀 Готово к загрузке на Yandex Cloud!"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Загрузите $ARCHIVE_NAME в Cloud Function через веб-интерфейс"
echo "   2. Или используйте скрипт: ./deploy_to_yandex_cloud.sh"
echo "   3. Или следуйте инструкциям в PERPLEXITY_INSTRUCTIONS.md"

