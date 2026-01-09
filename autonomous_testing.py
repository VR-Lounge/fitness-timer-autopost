#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Автономная система тестирования и проверки кода
    Senior-level автоматизация для Cursor
    
    Автоматически:
    - Проверяет синтаксис Python
    - Тестирует импорты модулей
    - Проверяет конфигурацию
    - Тестирует API подключения
    - Ищет потенциальные баги
    - Генерирует отчеты
"""

import os
import sys
import subprocess
import importlib
import ast
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import traceback

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class AutonomousTester:
    """Автономный тестер кода"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors = []
        self.warnings = []
        self.success = []
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'errors': [],
            'warnings': [],
            'success': [],
            'summary': {}
        }
    
    def log_error(self, message: str, file: str = None):
        """Логирует ошибку"""
        error = {'message': message, 'file': file}
        self.errors.append(error)
        self.report['errors'].append(error)
        print(f"{Colors.RED}❌ ОШИБКА:{Colors.RESET} {message}" + (f" ({file})" if file else ""))
    
    def log_warning(self, message: str, file: str = None):
        """Логирует предупреждение"""
        warning = {'message': message, 'file': file}
        self.warnings.append(warning)
        self.report['warnings'].append(warning)
        print(f"{Colors.YELLOW}⚠️  ПРЕДУПРЕЖДЕНИЕ:{Colors.RESET} {message}" + (f" ({file})" if file else ""))
    
    def log_success(self, message: str, file: str = None):
        """Логирует успех"""
        success = {'message': message, 'file': file}
        self.success.append(success)
        self.report['success'].append(success)
        print(f"{Colors.GREEN}✅ УСПЕХ:{Colors.RESET} {message}" + (f" ({file})" if file else ""))
    
    def check_python_syntax(self, file_path: Path) -> bool:
        """Проверяет синтаксис Python файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            ast.parse(code)
            return True
        except SyntaxError as e:
            self.log_error(f"Синтаксическая ошибка: {e.msg} (строка {e.lineno})", str(file_path))
            return False
        except Exception as e:
            self.log_error(f"Ошибка при проверке синтаксиса: {e}", str(file_path))
            return False
    
    def check_imports(self, file_path: Path) -> bool:
        """Проверяет импорты в файле"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            tree = ast.parse(code)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Проверяем доступность импортов
            missing = []
            for imp in imports:
                try:
                    # Пропускаем стандартные библиотеки
                    if imp.split('.')[0] in ['os', 'sys', 'json', 'datetime', 'pathlib', 'typing', 're', 'html', 'urllib', 'xml', 'time']:
                        continue
                    importlib.import_module(imp.split('.')[0])
                except ImportError:
                    missing.append(imp)
            
            if missing:
                self.log_warning(f"Потенциально отсутствующие импорты: {', '.join(missing)}", str(file_path))
                return False
            
            return True
        except Exception as e:
            self.log_error(f"Ошибка при проверке импортов: {e}", str(file_path))
            return False
    
    def check_configuration(self) -> bool:
        """Проверяет конфигурацию проекта"""
        required_env = [
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID',
            'DEEPSEEK_API_KEY'
        ]
        
        missing = []
        for env_var in required_env:
            if not os.getenv(env_var):
                missing.append(env_var)
        
        if missing:
            self.log_warning(f"Отсутствуют переменные окружения: {', '.join(missing)}")
            return False
        
        self.log_success("Все необходимые переменные окружения присутствуют")
        return True
    
    def check_file_structure(self) -> bool:
        """Проверяет структуру файлов проекта"""
        required_files = [
            'menshealth_parser.py',
            'auto_reply.py',
            'statistics.py',
            'requirements.txt',
            '.github/workflows/menshealth-parser.yml'
        ]
        
        missing = []
        for file_rel in required_files:
            file_path = self.project_root / file_rel
            if not file_path.exists():
                missing.append(file_rel)
        
        if missing:
            self.log_error(f"Отсутствуют файлы: {', '.join(missing)}")
            return False
        
        self.log_success("Все необходимые файлы присутствуют")
        return True
    
    def test_api_connections(self) -> bool:
        """Тестирует подключения к API"""
        import requests
        
        # Тест Telegram API
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if token:
            try:
                url = f"https://api.telegram.org/bot{token}/getMe"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    self.log_success("Telegram API доступен")
                else:
                    self.log_error(f"Telegram API недоступен: {response.status_code}")
                    return False
            except Exception as e:
                self.log_warning(f"Не удалось проверить Telegram API: {e}")
        
        # Тест DeepSeek API
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if api_key:
            try:
                url = "https://api.deepseek.com/v1/models"
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    self.log_success("DeepSeek API доступен")
                else:
                    self.log_warning(f"DeepSeek API недоступен: {response.status_code}")
            except Exception as e:
                self.log_warning(f"Не удалось проверить DeepSeek API: {e}")
        
        return True
    
    def check_potential_bugs(self, file_path: Path) -> List[Dict]:
        """Ищет потенциальные баги в коде"""
        bugs = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                lines = code.split('\n')
            
            # Проверяем на типичные ошибки
            for i, line in enumerate(lines, 1):
                # Проверка на необработанные исключения
                if 'except:' in line and 'except Exception:' not in line:
                    bugs.append({
                        'line': i,
                        'type': 'bare_except',
                        'message': 'Использование bare except может скрыть ошибки'
                    })
                
                # Проверка на хардкод секретов
                if any(keyword in line.lower() for keyword in ['password', 'token', 'api_key', 'secret']):
                    if 'os.getenv' not in line and 'os.environ' not in line:
                        if not any(comment in line for comment in ['#', '"""', "'''"]):
                            bugs.append({
                                'line': i,
                                'type': 'hardcoded_secret',
                                'message': 'Возможный хардкод секрета'
                            })
                
                # Проверка на SQL injection (если есть SQL)
                if 'execute(' in line and '%' in line:
                    bugs.append({
                        'line': i,
                        'type': 'sql_injection',
                        'message': 'Потенциальная уязвимость SQL injection'
                    })
            
            if bugs:
                for bug in bugs:
                    self.log_warning(f"{bug['message']} (строка {bug['line']})", str(file_path))
            
        except Exception as e:
            self.log_error(f"Ошибка при поиске багов: {e}", str(file_path))
        
        return bugs
    
    def test_module_import(self, module_name: str) -> bool:
        """Тестирует импорт модуля"""
        try:
            sys.path.insert(0, str(self.project_root))
            importlib.import_module(module_name)
            self.log_success(f"Модуль {module_name} успешно импортирован")
            return True
        except Exception as e:
            self.log_error(f"Не удалось импортировать {module_name}: {e}")
            return False
    
    def run_all_tests(self):
        """Запускает все тесты"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}🚀 АВТОНОМНОЕ ТЕСТИРОВАНИЕ{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
        
        # 1. Проверка структуры файлов
        print(f"{Colors.BOLD}📁 Проверка структуры файлов...{Colors.RESET}")
        self.check_file_structure()
        print()
        
        # 2. Проверка синтаксиса Python
        print(f"{Colors.BOLD}🐍 Проверка синтаксиса Python...{Colors.RESET}")
        python_files = list(self.project_root.glob('*.py'))
        for py_file in python_files:
            if py_file.name != '__init__.py':
                self.check_python_syntax(py_file)
        print()
        
        # 3. Проверка импортов
        print(f"{Colors.BOLD}📦 Проверка импортов...{Colors.RESET}")
        for py_file in python_files:
            if py_file.name != '__init__.py':
                self.check_imports(py_file)
        print()
        
        # 4. Поиск потенциальных багов
        print(f"{Colors.BOLD}🐛 Поиск потенциальных багов...{Colors.RESET}")
        for py_file in python_files:
            if py_file.name != '__init__.py':
                self.check_potential_bugs(py_file)
        print()
        
        # 5. Тестирование импорта модулей
        print(f"{Colors.BOLD}🧪 Тестирование импорта модулей...{Colors.RESET}")
        modules_to_test = ['menshealth_parser', 'auto_reply', 'statistics']
        for module in modules_to_test:
            if (self.project_root / f"{module}.py").exists():
                self.test_module_import(module)
        print()
        
        # 6. Проверка конфигурации
        print(f"{Colors.BOLD}⚙️  Проверка конфигурации...{Colors.RESET}")
        self.check_configuration()
        print()
        
        # 7. Тестирование API подключений
        print(f"{Colors.BOLD}🌐 Тестирование API подключений...{Colors.RESET}")
        self.test_api_connections()
        print()
        
        # Генерация отчета
        self.generate_report()
    
    def generate_report(self):
        """Генерирует отчет о тестировании"""
        self.report['summary'] = {
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'total_success': len(self.success),
            'status': 'PASS' if len(self.errors) == 0 else 'FAIL'
        }
        
        report_file = self.project_root / 'test_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}📊 ИТОГОВЫЙ ОТЧЁТ{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
        
        print(f"{Colors.GREEN}✅ Успешно: {len(self.success)}{Colors.RESET}")
        print(f"{Colors.YELLOW}⚠️  Предупреждения: {len(self.warnings)}{Colors.RESET}")
        print(f"{Colors.RED}❌ Ошибки: {len(self.errors)}{Colors.RESET}")
        print(f"\n📄 Полный отчёт сохранён в: {report_file}")
        
        if len(self.errors) == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!{Colors.RESET}\n")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}⚠️  ОБНАРУЖЕНЫ ОШИБКИ!{Colors.RESET}\n")

def main():
    """Главная функция"""
    project_root = Path(__file__).parent
    tester = AutonomousTester(project_root)
    tester.run_all_tests()

if __name__ == '__main__':
    main()
