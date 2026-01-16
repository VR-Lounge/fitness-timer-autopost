#!/bin/bash

# Скрипт для проверки DNS-резолвинга tabatatimer.ru

echo "🔍 Проверка DNS для tabatatimer.ru..."
echo ""

# Проверка через nslookup
echo "📊 Результат nslookup:"
nslookup tabatatimer.ru

echo ""
echo "📊 Результат dig:"
dig tabatatimer.ru +short

echo ""
echo "✅ Ожидаемые IP-адреса GitHub Pages:"
echo "  - 185.199.108.153"
echo "  - 185.199.109.153"
echo "  - 185.199.110.153"
echo "  - 185.199.111.153"

