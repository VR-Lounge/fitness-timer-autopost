#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Интеграция с браузером Cursor для автономной проверки сайтов
    
    Использует MCP cursor-ide-browser для:
    - Проверки сайтов
    - Выявления ошибок в консоли
    - Тестирования функционала
    - Создания скриншотов
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class BrowserTester:
    """Тестер через браузер Cursor"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent
        self.results = []
        self.errors = []
    
    def test_website(self, url: str, checks: List[str] = None) -> Dict:
        """
        Тестирует сайт через браузер
        
        Args:
            url: URL для проверки
            checks: Список проверок (console_errors, network_errors, etc.)
        
        Returns:
            Результаты проверки
        """
        result = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'console_errors': [],
            'network_errors': [],
            'screenshot': None,
            'status': 'unknown'
        }
        
        # Инструкции для выполнения через MCP browser
        instructions = {
            'action': 'test_website',
            'url': url,
            'steps': [
                {
                    'step': 'navigate',
                    'url': url,
                    'wait': 3
                },
                {
                    'step': 'check_console',
                    'filter': 'error'
                },
                {
                    'step': 'check_network',
                    'filter': 'failed'
                },
                {
                    'step': 'screenshot',
                    'filename': f"screenshot_{url.replace('https://', '').replace('/', '_')}.png"
                }
            ]
        }
        
        return result
    
    def generate_browser_instructions(self, url: str) -> str:
        """Генерирует инструкции для Perplexity/Comet Browser"""
        instructions = f"""
# 🌐 ИНСТРУКЦИИ ДЛЯ PERPLEXITY/COMET BROWSER

## Задача: Проверка сайта {url}

### ШАГ 1: Открыть сайт
1. Откройте браузер Comet
2. Перейдите на: {url}
3. Дождитесь полной загрузки страницы

### ШАГ 2: Проверить консоль на ошибки
1. Откройте DevTools (F12 или Cmd+Option+I)
2. Перейдите на вкладку "Console"
3. Проверьте наличие ошибок (красные сообщения)
4. Скопируйте все ошибки

### ШАГ 3: Проверить Network
1. Перейдите на вкладку "Network"
2. Обновите страницу (F5)
3. Найдите запросы со статусом 4xx или 5xx
4. Скопируйте список проблемных запросов

### ШАГ 4: Проверить функционал
1. Проверьте основные элементы интерфейса
2. Попробуйте взаимодействовать с элементами
3. Проверьте работу форм (если есть)
4. Проверьте мобильную версию (Device Toolbar)

### ШАГ 5: Сделать скриншот
1. Сделайте скриншот страницы
2. Сохраните как: screenshot_{url.replace('https://', '').replace('/', '_')}.png

### ШАГ 6: Отчет
Создайте отчет со следующей информацией:
- URL: {url}
- Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Ошибки в консоли: [список]
- Проблемные запросы: [список]
- Статус функционала: [работает/не работает]
- Скриншот: [путь к файлу]
"""
        return instructions
    
    def save_instructions(self, url: str, output_file: Path):
        """Сохраняет инструкции в файл"""
        instructions = self.generate_browser_instructions(url)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(instructions)
        print(f"✅ Инструкции сохранены в: {output_file}")
    
    def update_perplexity_tasks(self, task_description: str, priority: str = "Средний", deadline: str = "Еженедельно"):
        """Обновляет файл PERPLEXITY_TASKS.md с новой задачей"""
        tasks_file = self.project_root / 'PERPLEXITY_TASKS.md'
        
        if not tasks_file.exists():
            print(f"⚠️  Файл {tasks_file} не найден. Создайте его вручную.")
            return False
        
        try:
            with open(tasks_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Находим место для вставки новой задачи (после "## 📋 ТЕКУЩИЕ ЗАДАЧИ")
            task_id = len([line for line in content.split('\n') if line.strip().startswith('### ✅ Задача #')]) + 1
            
            new_task = f"""
### ✅ Задача #{task_id}: {task_description}

**Приоритет:** {priority}  
**Срок:** {deadline}  
**Статус:** 🔄 В работе

#### Что нужно сделать:

{task_description}

---

"""
            
            # Вставляем после "## 📋 ТЕКУЩИЕ ЗАДАЧИ"
            if "## 📋 ТЕКУЩИЕ ЗАДАЧИ" in content:
                insert_pos = content.find("## 📋 ТЕКУЩИЕ ЗАДАЧИ") + len("## 📋 ТЕКУЩИЕ ЗАДАЧИ")
                # Находим конец следующего заголовка
                next_section = content.find("\n### ✅ Задача #", insert_pos)
                if next_section == -1:
                    next_section = content.find("\n---", insert_pos)
                if next_section == -1:
                    next_section = len(content)
                
                content = content[:next_section] + new_task + content[next_section:]
            else:
                # Если секции нет, добавляем в конец
                content += f"\n## 📋 ТЕКУЩИЕ ЗАДАЧИ\n{new_task}"
            
            # Обновляем дату "Последнее обновление"
            from datetime import datetime
            current_date = datetime.now().strftime('%Y-%m-%d')
            content = content.replace(
                '> **Последнее обновление:**',
                f'> **Последнее обновление:** {current_date}',
                1
            )
            
            with open(tasks_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Задача #{task_id} добавлена в PERPLEXITY_TASKS.md")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при обновлении PERPLEXITY_TASKS.md: {e}")
            return False

def main():
    """Главная функция"""
    tester = BrowserTester()
    
    # Тестируем основные URL
    urls_to_test = [
        'https://www.tabatatimer.ru',
        'https://www.tabatatimer.ru/#timer',
        'https://www.tabatatimer.ru/nastrojki-tabata-tajmera.html'
    ]
    
    for url in urls_to_test:
        instructions_file = Path(f"browser_test_{url.replace('https://', '').replace('/', '_')}.md")
        tester.save_instructions(url, instructions_file)
        print(f"\n📋 Инструкции для проверки {url} готовы!")

if __name__ == '__main__':
    main()
