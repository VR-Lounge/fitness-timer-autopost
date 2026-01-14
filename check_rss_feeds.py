#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки RSS фидов на доступность и ошибки
"""

import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import time
from pathlib import Path

# Импортируем списки RSS фидов
import sys
sys.path.insert(0, str(Path(__file__).parent))

from womenshealth_parser import WOMENSHEALTH_RSS_FEEDS
from menshealth_parser import MENSHEALTH_RSS_FEEDS

def test_rss_feed(url, timeout=10):
    """Тестирует RSS фид на доступность"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            # Пробуем распарсить XML
            try:
                root = ET.fromstring(response.content)
                # Проверяем наличие элементов
                items = []
                if root.tag.endswith('feed'):  # Atom
                    items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
                elif root.tag == 'rss':  # RSS 2.0
                    channel = root.find('channel')
                    if channel is not None:
                        items = channel.findall('item')
                
                return {
                    'status': 'OK',
                    'status_code': 200,
                    'articles_count': len(items),
                    'error': None
                }
            except ET.ParseError as e:
                return {
                    'status': 'PARSE_ERROR',
                    'status_code': 200,
                    'articles_count': 0,
                    'error': f'Ошибка парсинга XML: {e}'
                }
        else:
            return {
                'status': 'ERROR',
                'status_code': response.status_code,
                'articles_count': 0,
                'error': f'HTTP {response.status_code}'
            }
    except requests.exceptions.Timeout:
        return {
            'status': 'TIMEOUT',
            'status_code': None,
            'articles_count': 0,
            'error': 'Таймаут'
        }
    except requests.exceptions.RequestException as e:
        return {
            'status': 'ERROR',
            'status_code': None,
            'articles_count': 0,
            'error': str(e)
        }
    except Exception as e:
        return {
            'status': 'UNKNOWN_ERROR',
            'status_code': None,
            'articles_count': 0,
            'error': str(e)
        }

def main():
    """Основная функция проверки"""
    print("="*80)
    print("ПРОВЕРКА RSS ФИДОВ НА ОШИБКИ")
    print("="*80)
    
    all_feeds = {
        'Девушки': WOMENSHEALTH_RSS_FEEDS,
        'Мужчины': MENSHEALTH_RSS_FEEDS
    }
    
    results = {
        'OK': [],
        'ERROR': [],
        'TIMEOUT': [],
        'PARSE_ERROR': [],
        'UNKNOWN_ERROR': []
    }
    
    for category, feeds in all_feeds.items():
        print(f"\n{'='*80}")
        print(f"Проверка RSS фидов для: {category}")
        print(f"Всего фидов: {len(feeds)}")
        print(f"{'='*80}\n")
        
        for i, url in enumerate(feeds, 1):
            print(f"[{i}/{len(feeds)}] Проверка: {url[:70]}...", end=' ', flush=True)
            result = test_rss_feed(url)
            
            status = result['status']
            results[status].append({
                'category': category,
                'url': url,
                'result': result
            })
            
            if status == 'OK':
                print(f"✅ OK ({result['articles_count']} статей)")
            elif status == 'ERROR':
                print(f"❌ {result['error']}")
            elif status == 'TIMEOUT':
                print(f"⏱️ Таймаут")
            elif status == 'PARSE_ERROR':
                print(f"⚠️ Ошибка парсинга")
            else:
                print(f"❓ {result['error']}")
            
            # Небольшая пауза между запросами
            time.sleep(0.5)
    
    # Итоговый отчет
    print("\n" + "="*80)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*80)
    
    total_feeds = sum(len(feeds) for feeds in all_feeds.values())
    total_ok = len(results['OK'])
    total_errors = total_feeds - total_ok
    
    print(f"\n📊 Статистика:")
    print(f"   Всего фидов: {total_feeds}")
    print(f"   ✅ Рабочих: {total_ok} ({total_ok/total_feeds*100:.1f}%)")
    print(f"   ❌ С ошибками: {total_errors} ({total_errors/total_feeds*100:.1f}%)")
    
    if results['ERROR']:
        print(f"\n❌ ОШИБКИ HTTP ({len(results['ERROR'])} фидов):")
        for item in results['ERROR']:
            print(f"   [{item['category']}] {item['url']}")
            print(f"      Ошибка: {item['result']['error']}")
    
    if results['TIMEOUT']:
        print(f"\n⏱️ ТАЙМАУТЫ ({len(results['TIMEOUT'])} фидов):")
        for item in results['TIMEOUT']:
            print(f"   [{item['category']}] {item['url']}")
    
    if results['PARSE_ERROR']:
        print(f"\n⚠️ ОШИБКИ ПАРСИНГА ({len(results['PARSE_ERROR'])} фидов):")
        for item in results['PARSE_ERROR']:
            print(f"   [{item['category']}] {item['url']}")
            print(f"      Ошибка: {item['result']['error']}")
    
    if results['UNKNOWN_ERROR']:
        print(f"\n❓ НЕИЗВЕСТНЫЕ ОШИБКИ ({len(results['UNKNOWN_ERROR'])} фидов):")
        for item in results['UNKNOWN_ERROR']:
            print(f"   [{item['category']}] {item['url']}")
            print(f"      Ошибка: {item['result']['error']}")
    
    # Список рабочих фидов
    print(f"\n✅ РАБОЧИЕ ФИДЫ ({total_ok}):")
    for category, feeds in all_feeds.items():
        working = [item for item in results['OK'] if item['category'] == category]
        if working:
            print(f"\n   {category} ({len(working)} фидов):")
            for item in working[:10]:  # Показываем первые 10
                print(f"      ✅ {item['url']} ({item['result']['articles_count']} статей)")
            if len(working) > 10:
                print(f"      ... и ещё {len(working) - 10} фидов")
    
    # Рекомендации
    print(f"\n📋 РЕКОМЕНДАЦИИ:")
    if total_errors > total_feeds * 0.3:  # Если больше 30% ошибок
        print(f"   ⚠️ Критично: {total_errors/total_feeds*100:.1f}% фидов не работают")
        print(f"   Рекомендуется удалить неработающие фиды из списков")
    else:
        print(f"   ✅ Большинство фидов работают ({total_ok/total_feeds*100:.1f}%)")
    
    if results['ERROR']:
        print(f"\n   Удалить из списков ({len(results['ERROR'])} фидов):")
        for item in results['ERROR']:
            print(f"      - {item['url']}")

if __name__ == '__main__':
    main()
