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
        """Проверяет статус GitHub Actions workflows через API"""
        status = {
            'workflows': [],
            'failed_runs': [],
            'errors': [],
            'status': 'unknown'
        }
        
        github_token = os.getenv('GITHUB_TOKEN')
        repo = os.getenv('GITHUB_REPOSITORY', 'VR-Lounge/fitness-timer-autopost')
        
        if not github_token:
            status['errors'].append("GITHUB_TOKEN не установлен")
            return status
        
        try:
            import requests
            
            # Получаем список workflows
            workflows_url = f"https://api.github.com/repos/{repo}/actions/workflows"
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(workflows_url, headers=headers, timeout=10)
            if response.status_code == 200:
                workflows_data = response.json()
                
                # Проверяем последние запуски каждого workflow
                important_workflows = [
                    'womenshealth-parser.yml',
                    'menshealth-parser.yml',
                    'autonomous-monitoring.yml'
                ]
                
                for workflow in workflows_data.get('workflows', []):
                    workflow_name = workflow.get('name', '')
                    workflow_path = workflow.get('path', '')
                    
                    if any(important in workflow_path for important in important_workflows):
                        # Получаем последние запуски
                        runs_url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow['id']}/runs?per_page=3"
                        runs_response = requests.get(runs_url, headers=headers, timeout=10)
                        
                        if runs_response.status_code == 200:
                            runs_data = runs_response.json()
                            for run in runs_data.get('workflow_runs', []):
                                run_status = run.get('status')
                                conclusion = run.get('conclusion')
                                
                                if conclusion == 'failure':
                                    status['failed_runs'].append({
                                        'workflow': workflow_name,
                                        'run_id': run.get('id'),
                                        'created_at': run.get('created_at'),
                                        'html_url': run.get('html_url')
                                    })
                                
                                status['workflows'].append({
                                    'name': workflow_name,
                                    'status': run_status,
                                    'conclusion': conclusion,
                                    'created_at': run.get('created_at')
                                })
                
                if status['failed_runs']:
                    status['status'] = 'error'
                else:
                    status['status'] = 'ok'
            else:
                status['errors'].append(f"Ошибка API GitHub: {response.status_code}")
                status['status'] = 'error'
                
        except Exception as e:
            status['errors'].append(f"Ошибка проверки workflows: {e}")
            status['status'] = 'error'
        
        return status
    
    def check_parser_status(self) -> Dict:
        """Проверяет статус обоих парсеров (Men's Health и Women's Health)"""
        status = {
            'menshealth': {
                'last_run': None,
                'articles_processed': 0,
                'errors': [],
                'status': 'unknown'
            },
            'womenshealth': {
                'last_run': None,
                'articles_processed': 0,
                'errors': [],
                'status': 'unknown'
            },
            'overall_status': 'unknown'
        }
        
        # Проверяем Men's Health парсер
        menshealth_file = self.project_root / '.menshealth_processed.json'
        if menshealth_file.exists():
            try:
                with open(menshealth_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    status['menshealth']['last_run'] = data.get('last_update')
                    status['menshealth']['articles_processed'] = len(data.get('articles', []))
                    status['menshealth']['status'] = 'active'
            except Exception as e:
                status['menshealth']['errors'].append(f"Ошибка чтения состояния: {e}")
                status['menshealth']['status'] = 'error'
        else:
            status['menshealth']['status'] = 'not_started'
        
        # Проверяем Women's Health парсер
        womenshealth_file = self.project_root / '.womenshealth_processed.json'
        if womenshealth_file.exists():
            try:
                with open(womenshealth_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    status['womenshealth']['last_run'] = data.get('last_update')
                    status['womenshealth']['articles_processed'] = len(data.get('articles', []))
                    status['womenshealth']['status'] = 'active'
            except Exception as e:
                status['womenshealth']['errors'].append(f"Ошибка чтения состояния: {e}")
                status['womenshealth']['status'] = 'error'
        else:
            status['womenshealth']['status'] = 'not_started'
        
        # Определяем общий статус
        if status['menshealth']['status'] == 'error' or status['womenshealth']['status'] == 'error':
            status['overall_status'] = 'error'
        elif status['menshealth']['status'] == 'active' and status['womenshealth']['status'] == 'active':
            status['overall_status'] = 'ok'
        else:
            status['overall_status'] = 'warning'
        
        return status
    
    def auto_fix_common_issues(self) -> List[str]:
        """Автоматически исправляет типичные проблемы (расширенная версия)"""
        fixes_applied = []
        
        # 1. Проверка и исправление импортов
        python_files = list(self.project_root.glob('*.py'))
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    original_content = content
                
                # Проверяем наличие необходимых импортов для парсеров
                if 'parser' in py_file.name:
                    required_imports = {
                        'menshealth_parser': ['from bs4 import BeautifulSoup', 'import requests', 'import json'],
                        'womenshealth_parser': ['from bs4 import BeautifulSoup', 'import requests', 'import json']
                    }
                    
                    for parser_type, imports in required_imports.items():
                        if parser_type in py_file.name:
                            for imp in imports:
                                if imp not in content:
                                    # Находим последний импорт
                                    lines = content.split('\n')
                                    last_import = 0
                                    for i, line in enumerate(lines):
                                        if line.strip().startswith('import ') or line.strip().startswith('from '):
                                            last_import = i
                                    
                                    lines.insert(last_import + 1, imp)
                                    content = '\n'.join(lines)
                                    fixes_applied.append(f"Добавлен импорт {imp} в {py_file.name}")
                
                # Проверка на отсутствующие переменные окружения
                if 'os.getenv' in content or 'os.environ' in content:
                    # Проверяем наличие проверок переменных окружения
                    if 'TELEGRAM_BOT_TOKEN' in content and 'if not' not in content.split('TELEGRAM_BOT_TOKEN')[0][-50:]:
                        # Добавляем проверку в начало функции main/главная
                        if 'def главная(' in content or 'def main(' in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if 'def главная(' in line or 'def main(' in line:
                                    # Ищем начало функции
                                    indent = len(line) - len(line.lstrip())
                                    # Добавляем проверку после docstring
                                    j = i + 1
                                    while j < len(lines) and (lines[j].strip().startswith('"""') or lines[j].strip().startswith("'''") or not lines[j].strip()):
                                        j += 1
                                    if j < len(lines):
                                        check_code = f"{' ' * (indent + 4)}if not os.getenv('TELEGRAM_BOT_TOKEN'):\n{' ' * (indent + 8)}print('⚠️ TELEGRAM_BOT_TOKEN не установлен')"
                                        lines.insert(j, check_code)
                                        content = '\n'.join(lines)
                                        fixes_applied.append(f"Добавлена проверка переменных окружения в {py_file.name}")
                                        break
                
                # Сохраняем изменения только если были исправления
                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
            except Exception as e:
                print(f"⚠️ Ошибка при проверке {py_file}: {e}")
        
        # 2. Проверка requirements.txt
        req_file = self.project_root / 'requirements.txt'
        if req_file.exists():
            with open(req_file, 'r', encoding='utf-8') as f:
                requirements = f.read()
            
            required_packages = ['beautifulsoup4', 'lxml', 'requests', 'scikit-learn']
            missing = []
            for package in required_packages:
                if package not in requirements and package.replace('-', '_') not in requirements:
                    missing.append(package)
            
            if missing:
                with open(req_file, 'a', encoding='utf-8') as f:
                    for package in missing:
                        f.write(f"\n{package}")
                fixes_applied.append(f"Добавлены пакеты в requirements.txt: {', '.join(missing)}")
        
        # 3. Проверка наличия необходимых файлов конфигурации
        config_files = {
            '.lighthouserc.json': '{}',
            '.gitignore': '.womenshealth_processed.json\n.menshealth_processed.json\n.content_hashes.json\n'
        }
        
        for config_file, default_content in config_files.items():
            config_path = self.project_root / config_file
            if not config_path.exists():
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(default_content)
                fixes_applied.append(f"Создан файл конфигурации: {config_file}")
        
        return fixes_applied
    
    def send_telegram_notification(self, message: str, is_critical: bool = False):
        """Отправляет уведомление в Telegram (только админу в личные сообщения)"""
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        # ВСЕГДА используем только ADMIN_TELEGRAM_CHAT_ID для административных уведомлений
        chat_id = os.getenv('ADMIN_TELEGRAM_CHAT_ID')
        
        if not bot_token:
            print("⚠️ TELEGRAM_BOT_TOKEN не настроен")
            return False
        
        if not chat_id:
            print("⚠️ ADMIN_TELEGRAM_CHAT_ID не настроен, уведомление не отправлено")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            emoji = "🚨" if is_critical else "⚠️"
            text = f"{emoji} **Автономный мониторинг**\n\n{message}"
            
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Ошибка отправки уведомления: {e}")
            return False
    
    def generate_monitoring_report(self) -> str:
        """Генерирует отчет о мониторинге"""
        parser_status = self.check_parser_status()
        workflow_status = self.check_workflow_status()
        fixes = self.auto_fix_common_issues()
        
        # Проверяем критические ошибки
        critical_errors = []
        if parser_status['overall_status'] == 'error':
            critical_errors.append("❌ Ошибки в работе парсеров")
        if workflow_status['status'] == 'error' and workflow_status['failed_runs']:
            critical_errors.append(f"❌ Упавшие workflows: {len(workflow_status['failed_runs'])}")
        
        # Отправляем уведомление при критических ошибках
        if critical_errors:
            notification = f"Обнаружены критические проблемы:\n\n" + "\n".join(critical_errors)
            self.send_telegram_notification(notification, is_critical=True)
        
        report = f"""
# 📊 ОТЧЁТ АВТОНОМНОГО МОНИТОРИНГА

**Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🔍 Статус парсеров

### Men's Health:
- **Статус:** {parser_status['menshealth']['status']}
- **Последний запуск:** {parser_status['menshealth']['last_run'] or 'Неизвестно'}
- **Обработано статей:** {parser_status['menshealth']['articles_processed']}
- **Ошибки:** {len(parser_status['menshealth']['errors'])}

### Women's Health:
- **Статус:** {parser_status['womenshealth']['status']}
- **Последний запуск:** {parser_status['womenshealth']['last_run'] or 'Неизвестно'}
- **Обработано статей:** {parser_status['womenshealth']['articles_processed']}
- **Ошибки:** {len(parser_status['womenshealth']['errors'])}

### Общий статус: {parser_status['overall_status']}

## 🔄 Статус GitHub Actions Workflows

- **Статус:** {workflow_status['status']}
- **Проверено workflows:** {len(workflow_status['workflows'])}
- **Упавших запусков:** {len(workflow_status['failed_runs'])}

"""
        
        if workflow_status['failed_runs']:
            report += "\n### Упавшие workflows:\n"
            for failed in workflow_status['failed_runs'][:5]:  # Показываем первые 5
                report += f"- ❌ {failed['workflow']} (ID: {failed['run_id']})\n"
        
        report += f"""
## 🔧 Автоматические исправления

Исправлено проблем: {len(fixes)}
"""
        
        if fixes:
            report += "\n### Применённые исправления:\n"
            for fix in fixes:
                report += f"- ✅ {fix}\n"
        else:
            report += "\n✅ Проблем не обнаружено\n"
        
        if parser_status['menshealth']['errors']:
            report += "\n### Ошибки Men's Health:\n"
            for error in parser_status['menshealth']['errors']:
                report += f"- ❌ {error}\n"
        
        if parser_status['womenshealth']['errors']:
            report += "\n### Ошибки Women's Health:\n"
            for error in parser_status['womenshealth']['errors']:
                report += f"- ❌ {error}\n"
        
        if workflow_status['errors']:
            report += "\n### Ошибки проверки workflows:\n"
            for error in workflow_status['errors']:
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
    
    # Проверка статуса парсеров
    parser_status = monitor.check_parser_status()
    print(f"📊 Статус парсеров: {parser_status['overall_status']}")
    
    # Проверка статуса workflows
    workflow_status = monitor.check_workflow_status()
    print(f"🔄 Статус workflows: {workflow_status['status']}")
    if workflow_status['failed_runs']:
        print(f"⚠️ Обнаружено упавших запусков: {len(workflow_status['failed_runs'])}")
    
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
    
    # Отправка краткого уведомления при успешной проверке
    if parser_status['overall_status'] == 'ok' and workflow_status['status'] == 'ok':
        monitor.send_telegram_notification(
            f"✅ Мониторинг завершён успешно\n\n"
            f"Парсеры: {parser_status['menshealth']['articles_processed'] + parser_status['womenshealth']['articles_processed']} статей\n"
            f"Workflows: {len(workflow_status['workflows'])} проверено\n"
            f"Исправлений: {len(fixes)}",
            is_critical=False
        )

if __name__ == '__main__':
    main()
