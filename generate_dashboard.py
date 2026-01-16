#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Генератор dashboard для мониторинга публикаций
    
    Создает HTML dashboard с метриками, статистикой и предупреждениями
    о дисбалансе тематик. Доступен только владельцу сайта.
    
    Автор: VR-Lounge
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))
from topic_balance import получить_статистику_баланса_за_период
from publication_logger import получить_статистику_публикаций, проверить_дисбаланс_тематик

DASHBOARD_FILE = Path('public_html/admin/dashboard.html')

def создать_dashboard():
    """Создает HTML dashboard с метриками"""
    
    # Получаем статистику
    статистика_7_дней = получить_статистику_публикаций(7)
    статистика_30_дней = получить_статистику_публикаций(30)
    баланс_7_дней = получить_статистику_баланса_за_период(7)
    предупреждение = проверить_дисбаланс_тематик(7)
    
    # Генерируем HTML
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Мониторинг публикаций TABATATIMER.RU</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .header h1 {{
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            color: #666;
            font-size: 1.1em;
        }}
        .warning {{
            background: #ff6b6b;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 5px 15px rgba(255,107,107,0.3);
        }}
        .warning h2 {{
            margin-bottom: 10px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 1.5em;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        .metric:last-child {{
            border-bottom: none;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.95em;
        }}
        .metric-value {{
            color: #333;
            font-weight: bold;
            font-size: 1.2em;
        }}
        .progress-bar {{
            width: 100%;
            height: 25px;
            background: #f0f0f0;
            border-radius: 12px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.85em;
            font-weight: bold;
            transition: width 0.3s ease;
        }}
        .topic-stats {{
            margin-top: 15px;
        }}
        .topic-item {{
            margin: 10px 0;
        }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 20px;
        }}
        .badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .badge-success {{
            background: #51cf66;
            color: white;
        }}
        .badge-warning {{
            background: #ffd43b;
            color: #333;
        }}
        .badge-danger {{
            background: #ff6b6b;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Dashboard - Мониторинг публикаций</h1>
            <p>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
        </div>
"""
    
    # Предупреждение о дисбалансе
    if предупреждение:
        html += f"""
        <div class="warning">
            <h2>⚠️ {предупреждение['предупреждение']}</h2>
            <ul style="margin-top: 10px; margin-left: 20px;">
"""
        for дисбаланс in предупреждение.get('дисбалансы', []):
            html += f"""
                <li>{дисбаланс['тема']}: фактически {дисбаланс['фактический_процент']:.1f}% (цель: {дисбаланс['целевой_процент']}%, отклонение: {дисбаланс['отклонение']:.1f}%)</li>
"""
        html += """
            </ul>
            <p style="margin-top: 10px;"><strong>Рекомендация:</strong> {}</p>
        </div>
""".format(предупреждение.get('рекомендация', ''))
    
    # Метрики за 7 дней
    всего_7 = статистика_7_дней.get('всего_публикаций', 0)
    на_сайт_7 = статистика_7_дней.get('на_сайт', 0)
    в_telegram_7 = статистика_7_дней.get('в_telegram', 0)
    
    html += f"""
        <div class="grid">
            <div class="card">
                <h2>📈 Публикации за 7 дней</h2>
                <div class="metric">
                    <span class="metric-label">Всего публикаций</span>
                    <span class="metric-value">{всего_7}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">На сайт</span>
                    <span class="metric-value">{на_сайт_7}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">В Telegram</span>
                    <span class="metric-value">{в_telegram_7}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Ожидалось (сайт)</span>
                    <span class="metric-value">21 <span class="badge {'badge-success' if на_сайт_7 >= 18 else 'badge-warning' if на_сайт_7 >= 15 else 'badge-danger'}">{(на_сайт_7/21*100):.0f}%</span></span>
                </div>
            </div>
"""
    
    # Статистика по тегам за 7 дней
    статистика_тегов = статистика_7_дней.get('статистика_тегов', {})
    html += f"""
            <div class="card">
                <h2>🏷️ Тематики за 7 дней</h2>
"""
    целевое = {'Тренировка': 40, 'Питание': 30, 'Диеты': 15, 'Мотивация': 15}
    for тема, целевой_процент in целевое.items():
        количество = статистика_тегов.get(тема, 0)
        фактический_процент = (количество / всего_7 * 100) if всего_7 > 0 else 0
        отклонение = abs(фактический_процент - целевой_процент)
        badge_class = 'badge-success' if отклонение < 10 else 'badge-warning' if отклонение < 20 else 'badge-danger'
        
        html += f"""
                <div class="topic-item">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span><strong>{тема}</strong></span>
                        <span>{количество} ({фактический_процент:.1f}%) <span class="badge {badge_class}">цель: {целевой_процент}%</span></span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {min(100, фактический_процент)}%;">{фактический_процент:.1f}%</div>
                    </div>
                </div>
"""
    
    html += """
            </div>
"""
    
    # Статистика по аудитории
    статистика_аудитории = статистика_7_дней.get('статистика_аудитории', {})
    html += f"""
            <div class="card">
                <h2>👥 Аудитория за 7 дней</h2>
"""
    for аудитория, количество in статистика_аудитории.items():
        процент = (количество / всего_7 * 100) if всего_7 > 0 else 0
        html += f"""
                <div class="metric">
                    <span class="metric-label">{аудитория}</span>
                    <span class="metric-value">{количество} ({процент:.1f}%)</span>
                </div>
"""
    html += """
            </div>
"""
    
    # Метрики за 30 дней
    статистика_30 = статистика_30_дней.get('всего_публикаций', 0)
    html += f"""
            <div class="card">
                <h2>📊 Публикации за 30 дней</h2>
                <div class="metric">
                    <span class="metric-label">Всего публикаций</span>
                    <span class="metric-value">{статистика_30}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">На сайт</span>
                    <span class="metric-value">{статистика_30_дней.get('на_сайт', 0)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">В Telegram</span>
                    <span class="metric-value">{статистика_30_дней.get('в_telegram', 0)}</span>
                </div>
            </div>
"""
    
    html += """
        </div>
        <div class="footer">
            <p>🔒 Приватный dashboard - только для владельца сайта</p>
            <p>Данные обновляются автоматически при каждой публикации</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Сохраняем dashboard
    DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Dashboard создан: {DASHBOARD_FILE}")

if __name__ == '__main__':
    создать_dashboard()
