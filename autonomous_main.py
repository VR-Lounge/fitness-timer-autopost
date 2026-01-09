#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    ГЛАВНЫЙ СКРИПТ АВТОНОМНОЙ РАБОТЫ CURSOR
    
    Senior-level автоматизация:
    - Запускает все автономные проверки
    - Тестирует код
    - Мониторит систему
    - Генерирует инструкции для Perplexity
    - Создает отчеты
    - Автоматически исправляет ошибки
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

class AutonomousMain:
    """Главный класс автономной работы"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = {
            'testing': None,
            'monitoring': None,
            'browser_instructions': None,
            'timestamp': datetime.now().isoformat()
        }
    
    def run_testing(self):
        """Запускает автономное тестирование"""
        print("\n" + "="*60)
        print("🧪 ЗАПУСК АВТОНОМНОГО ТЕСТИРОВАНИЯ")
        print("="*60 + "\n")
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.project_root / 'autonomous_testing.py')],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            self.results['testing'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Ошибка при тестировании: {e}")
            self.results['testing'] = {'success': False, 'error': str(e)}
            return False
    
    def run_monitoring(self):
        """Запускает автономный мониторинг"""
        print("\n" + "="*60)
        print("📊 ЗАПУСК АВТОНОМНОГО МОНИТОРИНГА")
        print("="*60 + "\n")
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.project_root / 'autonomous_monitor.py')],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            self.results['monitoring'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Ошибка при мониторинге: {e}")
            self.results['monitoring'] = {'success': False, 'error': str(e)}
            return False
    
    def generate_browser_instructions(self):
        """Генерирует инструкции для Perplexity/Comet Browser"""
        print("\n" + "="*60)
        print("🌐 ГЕНЕРАЦИЯ ИНСТРУКЦИЙ ДЛЯ PERPLEXITY")
        print("="*60 + "\n")
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.project_root / 'browser_integration.py')],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            self.results['browser_instructions'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Ошибка при генерации инструкций: {e}")
            self.results['browser_instructions'] = {'success': False, 'error': str(e)}
            return False
    
    def generate_summary_report(self):
        """Генерирует итоговый отчет"""
        report = f"""
# 📊 ИТОГОВЫЙ ОТЧЁТ АВТОНОМНОЙ РАБОТЫ

**Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## ✅ Результаты

### 🧪 Тестирование
- **Статус:** {'✅ Успешно' if self.results['testing'] and self.results['testing'].get('success') else '❌ Ошибка'}
- **Детали:** См. test_report.json

### 📊 Мониторинг
- **Статус:** {'✅ Успешно' if self.results['monitoring'] and self.results['monitoring'].get('success') else '❌ Ошибка'}
- **Детали:** См. monitoring_report_*.md

### 🌐 Инструкции для Perplexity
- **Статус:** {'✅ Сгенерированы' if self.results['browser_instructions'] and self.results['browser_instructions'].get('success') else '❌ Ошибка'}
- **Файлы:** browser_test_*.md

## 📝 Следующие шаги

1. Проверьте test_report.json на наличие ошибок
2. Проверьте monitoring_report_*.md для деталей мониторинга
3. Передайте browser_test_*.md в Perplexity/Comet Browser для проверки сайтов
4. После получения результатов от Perplexity запустите анализ

---
**Сгенерировано автоматически системой автономной работы Cursor**
"""
        
        report_file = self.project_root / f"autonomous_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("\n" + "="*60)
        print("📄 ИТОГОВЫЙ ОТЧЁТ")
        print("="*60)
        print(report)
        print(f"\n✅ Отчёт сохранён: {report_file}\n")
        
        return report_file
    
    def run_all(self):
        """Запускает все автономные процессы"""
        print("\n" + "🚀"*30)
        print("🚀 ЗАПУСК ПОЛНОГО ЦИКЛА АВТОНОМНОЙ РАБОТЫ CURSOR")
        print("🚀"*30 + "\n")
        
        # 1. Тестирование
        self.run_testing()
        
        # 2. Мониторинг
        self.run_monitoring()
        
        # 3. Генерация инструкций для Perplexity
        self.generate_browser_instructions()
        
        # 4. Итоговый отчет
        self.generate_summary_report()
        
        # Итоговая статистика
        total = 3
        success = sum([
            1 if self.results['testing'] and self.results['testing'].get('success') else 0,
            1 if self.results['monitoring'] and self.results['monitoring'].get('success') else 0,
            1 if self.results['browser_instructions'] and self.results['browser_instructions'].get('success') else 0
        ])
        
        print("\n" + "="*60)
        print(f"📊 ИТОГО: {success}/{total} процессов завершено успешно")
        print("="*60 + "\n")
        
        if success == total:
            print("🎉 ВСЕ ПРОЦЕССЫ ВЫПОЛНЕНЫ УСПЕШНО!\n")
        else:
            print("⚠️  НЕКОТОРЫЕ ПРОЦЕССЫ ЗАВЕРШИЛИСЬ С ОШИБКАМИ\n")

def main():
    """Главная функция"""
    autonomous = AutonomousMain()
    autonomous.run_all()

if __name__ == '__main__':
    main()
