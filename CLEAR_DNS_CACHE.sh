#!/bin/bash

# Скрипт для очистки DNS-кэша на macOS
# Использование: sudo ./clear_dns_cache.sh

echo "🔄 Очистка DNS-кэша macOS..."
echo ""

# Очистка кэша DNS
sudo dscacheutil -flushcache

# Перезапуск mDNSResponder
sudo killall -HUP mDNSResponder

echo ""
echo "✅ DNS-кэш успешно очищен!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Перезапусти браузер"
echo "2. Попробуй открыть: https://tabatatimer.ru"
echo ""
echo "🔍 Проверка DNS:"
echo "Выполни команду: nslookup tabatatimer.ru"
echo "Должны вернуться IP-адреса GitHub Pages:"
echo "  - 185.199.108.153"
echo "  - 185.199.109.153"
echo "  - 185.199.110.153"
echo "  - 185.199.111.153"
