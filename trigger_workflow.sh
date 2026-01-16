#!/bin/bash
# Скрипт для запуска GitHub Actions workflow через API

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Запуск GitHub Actions workflow...${NC}"

# Проверка наличия GitHub CLI
if command -v gh &> /dev/null; then
    echo -e "${GREEN}✅ GitHub CLI найден${NC}"
    
    # Проверка авторизации
    if gh auth status &> /dev/null; then
        echo -e "${GREEN}✅ Авторизован в GitHub${NC}"
        
        # Получаем информацию о репозитории
        REPO=$(git remote get-url origin 2>/dev/null | sed -E 's/.*github.com[:/]([^/]+\/[^/]+)(\.git)?$/\1/')
        
        if [ -z "$REPO" ]; then
            echo -e "${RED}❌ Не удалось определить репозиторий${NC}"
            echo "Убедитесь, что вы находитесь в директории с git репозиторием"
            exit 1
        fi
        
        echo -e "${YELLOW}📦 Репозиторий: $REPO${NC}"
        
        # Запускаем workflow
        echo -e "${YELLOW}🔄 Запускаем workflow 'Автоматический ответ на комментарии'...${NC}"
        
        WORKFLOW_ID=$(gh workflow list --repo "$REPO" 2>/dev/null | grep "Автоматический ответ" | awk '{print $NF}' | head -1)
        
        if [ -z "$WORKFLOW_ID" ]; then
            # Пробуем найти по имени файла
            WORKFLOW_ID=$(gh workflow list --repo "$REPO" 2>/dev/null | grep "auto-reply" | awk '{print $NF}' | head -1)
        fi
        
        if [ -z "$WORKFLOW_ID" ]; then
            echo -e "${RED}❌ Не удалось найти workflow${NC}"
            echo "Доступные workflows:"
            gh workflow list --repo "$REPO" 2>/dev/null || echo "Не удалось получить список"
            exit 1
        fi
        
        echo -e "${YELLOW}📋 Workflow ID: $WORKFLOW_ID${NC}"
        
        # Запускаем
        RUN_ID=$(gh workflow run "$WORKFLOW_ID" --repo "$REPO" 2>&1)
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Workflow запущен!${NC}"
            echo -e "${YELLOW}⏳ Ожидаем 5 секунд...${NC}"
            sleep 5
            
            # Получаем информацию о запуске
            echo -e "${YELLOW}📊 Проверяем статус...${NC}"
            gh run list --workflow="$WORKFLOW_ID" --repo "$REPO" --limit 1
            
            echo ""
            echo -e "${GREEN}✅ Для просмотра логов выполните:${NC}"
            echo "   gh run watch --repo $REPO"
            echo ""
            echo -e "${GREEN}Или откройте в браузере:${NC}"
            echo "   https://github.com/$REPO/actions"
        else
            echo -e "${RED}❌ Ошибка запуска workflow${NC}"
            echo "$RUN_ID"
            exit 1
        fi
    else
        echo -e "${RED}❌ Не авторизован в GitHub CLI${NC}"
        echo "Выполните: gh auth login"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️ GitHub CLI не установлен${NC}"
    echo ""
    echo "Установите GitHub CLI:"
    echo "  macOS: brew install gh"
    echo "  Linux: см. https://cli.github.com/manual/installation"
    echo ""
    echo "Или запустите workflow вручную:"
    echo "  1. Откройте https://github.com/LOBANOFF-PRO/tabatatimer.ru/actions"
    echo "  2. Выберите '🔄 Автоматический ответ на комментарии'"
    echo "  3. Нажмите 'Run workflow'"
    exit 1
fi

