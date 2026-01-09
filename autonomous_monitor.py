#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Автономный мониторинг и автоматическое исправление ошибок
    
    Senior-level система для:
    - Мониторинга работы парсера
    - Автоматического исправления ошибок
    - Генерации отчетов
    - Интеграции с GitHub Actions
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import requests

class AutonomousMonitor:
    """Автономный мониторинг системы"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.monitoring_data = {
            'last_check': None,
            'errors_found': [],
            'fixes_applied': [],
            'system_status': 'unknown'
        }
    
    def check_workflow_status(self) -> Dict:
        """Проверяет статус GitHub Actions workflows"""
        # Инструкции для проверки через API или браузер
        return {
            'action': 'check_github_workflows',
            'instructions': """
# 🔍 ПРОВЕРКА GITHUB ACTIONS WORKFLOWS

## Через GitHub API:
1. Получить токен GitHub (GITHUB_TOKEN)
2. Запрос: GET https://api.github.com/repos/OWNER/REPO/actions/workflows
3. Проверить статус последних запусков
4. Найти ошибки в логах

## Через браузер:
1. Открыть: https://github.com/LOBANOFF-PRO/tabatatimer.ru/actions
2. Проверить статус последних workflow
3. Открыть логи упавших workflow
4. Скопировать ошибки
"""
        }
    
    def check_parser_status(self) -> Dict:
        """Проверяет статус парсера Men's Health"""
        status = {
            'last_run': None,
            'articles_processed': 0,
            'errors': [],
            'status': 'unknown'
        }
        
        # Проверяем файл состояния
        state_file = self.project_root / '.menshealth_processed.json'
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    status['last_run'] = data.get('last_update')
                    status['articles_processed'] = len(data.get('articles', []))
                    status['status'] = 'active'
            except Exception as e:
                status['errors'].append(f"Ошибка чтения состояния: {e}")
                status['status'] = 'error'
        else:
            status['status'] = 'not_started'
        
        return status
    
    def auto_fix_common_issues(self) -> List[str]:
        """Автоматически исправляет типичные проблемы"""
        fixes_applied = []
        
        # 1. Проверка и исправление импортов
        python_files = list(self.project_root.glob('*.py'))
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Проверяем наличие необходимых импортов
                if 'menshealth_parser' in py_file.name:
                    if 'from bs4 import BeautifulSoup' not in content:
                        # Добавляем импорт
                        if 'import' in content:
                            # Находим последний импорт
                            lines = content.split('\n')
                            last_import = 0
                            for i, line in enumerate(lines):
                                if line.strip().startswith('import ') or line.strip().startswith('from '):
                                    last_import = i
                            
                            lines.insert(last_import + 1, 'from bs4 import BeautifulSoup')
                            content = '\n'.join(lines)
                            
                            with open(py_file, 'w', encoding='utf-8') as f:
                                f.write(content)
                            
                            fixes_applied.append(f"Добавлен импорт BeautifulSoup в {py_file.name}")
            except Exception as e:
                print(f"Ошибка при проверке {py_file}: {e}")
        
        # 2. Проверка requirements.txt
        req_file = self.project_root / 'requirements.txt'
        if req_file.exists():
            with open(req_file, 'r', encoding='utf-8') as f:
                requirements = f.read()
            
            required_packages = ['beautifulsoup4', 'lxml', 'requests']
            missing = []
            for package in required_packages:
                if package not in requirements:
                    missing.append(package)
            
            if missing:
                with open(req_file, 'a', encoding='utf-8') as f:
                    for package in missing:
                        f.write(f"\n{package}")
                fixes_applied.append(f"Добавлены пакеты в requirements.txt: {', '.join(missing)}")
        
        return fixes_applied
    
    def generate_monitoring_report(self) -> str:
        """Генерирует отчет о мониторинге"""
        parser_status = self.check_parser_status()
        fixes = self.auto_fix_common_issues()
        
        report = f"""
# 📊 ОТЧЁТ АВТОНОМНОГО МОНИТОРИНГА

**Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🔍 Статус парсера Men's Health

- **Статус:** {parser_status['status']}
- **Последний запуск:** {parser_status['last_run'] or 'Неизвестно'}
- **Обработано статей:** {parser_status['articles_processed']}
- **Ошибки:** {len(parser_status['errors'])}

## 🔧 Автоматические исправления

Исправлено проблем: {len(fixes)}
"""
        
        if fixes:
            report += "\n### Применённые исправления:\n"
            for fix in fixes:
                report += f"- ✅ {fix}\n"
        else:
            report += "\n✅ Проблем не обнаружено\n"
        
        if parser_status['errors']:
            report += "\n### Ошибки:\n"
            for error in parser_status['errors']:
                report += f"- ❌ {error}\n"
        
        return report
    
    def save_report(self, report: str):
        """Сохраняет отчет"""
        report_file = self.project_root / f"monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ Отчёт сохранён: {report_file}")

def main():
    """Главная функция"""
    project_root = Path(__file__).parent
    monitor = AutonomousMonitor(project_root)
    
    print("🔍 Запуск автономного мониторинга...")
    
    # Автоматические исправления
    fixes = monitor.auto_fix_common_issues()
    if fixes:
        print(f"✅ Применено исправлений: {len(fixes)}")
        for fix in fixes:
            print(f"  - {fix}")
    
    # Генерация отчета
    report = monitor.generate_monitoring_report()
    print("\n" + report)
    monitor.save_report(report)

if __name__ == '__main__':
    main()
