#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки новых RSS лент на релевантность и ошибки парсинга
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Tuple
import time

# Новые RSS ленты для проверки
NEW_WOMENS_FEEDS = [
    'https://strongfirst.com/blog/feed',
    'https://nourishmovelove.com/category/hiit/feed',
    'https://7-min.com/category/hiit/feed',
    'https://simpleendurancecoaching.com/category/hiit/feed',
    'https://polar.com/blog/tag/hiit-training/feed',
    'https://tone-and-tighten.com/category/strength-training/feed',
    'https://potentialpersonaltraining.co.uk/category/weight-training/feed',
    'https://strengthforendurance.com/strength-training/feed',
    'https://fasterfitness.com/category/training/feed',
    'https://juliabuckleyfitness.com/feed',
    'https://fitbottomedgirls.com/category/workouts/feed',
    'https://hungry-runner.com/category/fitness/strength-training/feed',
    'https://kingofthegym.com/training/feed',
    'https://wellnessmama.com/feed',
    'https://feeds.buzzsprout.com/2269359.rss',
    'https://feeds.buzzsprout.com/1776731.rss',
    'https://media.rss.com/thiccfit-fitness/feed.xml',
    'https://www.vickihill.co.uk/blog/feed',
    'https://rss.com/podcasts/muscle-strength-and-menopause/feed',
    'https://blog.feed.fm/feed',
]

NEW_MENS_FEEDS = [
    'https://startingstrength.com/rss.rss',
    'https://3dmusclejourney.com/blog.rss',
    'https://www.jimwendler.com/blogs/jimwendler-com.atom',
    'https://www.westside-barbell.com/blogs/the-blog.atom',
    'https://breakingmuscle.com/feed',
]

# Ключевые слова для проверки релевантности
RELEVANT_KEYWORDS = [
    'tabata', 'hiit', 'amrap', 'emom', 'interval training', 'interval workout',
    'high intensity', 'circuit training', 'timed workout', 'workout timer',
    'diet', 'nutrition', 'meal plan', 'protein', 'carb', 'calorie',
    'weight loss', 'fat loss', 'metabolism', 'meal prep', 'healthy eating',
    'workout', 'exercise', 'training', 'fitness', 'cardio', 'strength',
    'endurance', 'conditioning', 'burn fat', 'build muscle', 'toning',
    'women health', 'female fitness', 'hormones', 'period', 'menstrual',
    'pregnancy workout', 'postpartum', 'menopause', 'women wellness',
    'quick workout', 'home workout', 'bodyweight', 'no equipment',
    'short workout', 'efficient workout', 'effective training', 'yoga', 'pilates',
    'strength training', 'functional training', 'bodybuilding', 'crossfit',
    'powerlifting', 'kettlebell', 'barbell', 'weight training'
]

def check_rss_feed(url: str) -> Tuple[bool, Dict]:
    """Проверяет RSS ленту на доступность, парсинг и релевантность"""
    result = {
        'url': url,
        'status': 'unknown',
        'http_status': None,
        'parse_success': False,
        'articles_count': 0,
        'relevance_score': 0.0,
        'relevance_percentage': 0,
        'sample_titles': [],
        'error': None
    }
    
    try:
        # Проверка доступности
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        result['http_status'] = response.status_code
        
        if response.status_code != 200:
            result['status'] = 'error'
            result['error'] = f'HTTP {response.status_code}'
            return False, result
        
        # Парсинг XML
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            result['status'] = 'parse_error'
            result['error'] = f'XML Parse Error: {str(e)}'
            return False, result
        
        # Извлечение статей
        items = []
        if root.tag.endswith('feed') or '{http://www.w3.org/2005/Atom}feed' in root.tag:
            # Atom формат
            items = root.findall('{http://www.w3.org/2005/Atom}entry')
        else:
            # RSS формат
            channel = root.find('channel')
            if channel is not None:
                items = channel.findall('item')
            else:
                items = root.findall('.//item')
        
        result['articles_count'] = len(items)
        
        if len(items) == 0:
            result['status'] = 'no_articles'
            result['error'] = 'Нет статей в RSS'
            return False, result
        
        # Проверка релевантности
        relevant_count = 0
        sample_titles = []
        
        for item in items[:10]:  # Проверяем первые 10 статей
            title_elem = item.find('title') or item.find('.//title') or item.find('{http://www.w3.org/2005/Atom}title')
            desc_elem = item.find('description') or item.find('.//description') or item.find('{http://www.w3.org/2005/Atom}summary')
            
            title = (title_elem.text if title_elem is not None and title_elem.text else '').lower()
            desc = (desc_elem.text if desc_elem is not None and desc_elem.text else '').lower()
            
            combined_text = f"{title} {desc}"
            
            # Проверяем наличие ключевых слов
            keyword_matches = sum(1 for keyword in RELEVANT_KEYWORDS if keyword.lower() in combined_text)
            
            if keyword_matches > 0:
                relevant_count += 1
                if len(sample_titles) < 3:
                    title_text = title_elem.text if title_elem is not None and title_elem.text else 'Без заголовка'
                    sample_titles.append(title_text[:80])
        
        result['relevance_score'] = relevant_count / min(len(items), 10)
        result['relevance_percentage'] = int(result['relevance_score'] * 100)
        result['sample_titles'] = sample_titles
        result['parse_success'] = True
        
        # Определяем статус
        if result['relevance_percentage'] >= 60:
            result['status'] = 'high_relevance'
        elif result['relevance_percentage'] >= 40:
            result['status'] = 'medium_relevance'
        elif result['relevance_percentage'] >= 20:
            result['status'] = 'low_relevance'
        else:
            result['status'] = 'not_relevant'
        
        return True, result
        
    except requests.exceptions.Timeout:
        result['status'] = 'timeout'
        result['error'] = 'Timeout'
        return False, result
    except requests.exceptions.RequestException as e:
        result['status'] = 'error'
        result['error'] = f'Request Error: {str(e)}'
        return False, result
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f'Unexpected Error: {str(e)}'
        return False, result

def main():
    print("=" * 80)
    print("🔍 ПРОВЕРКА НОВЫХ RSS ЛЕНТ НА РЕЛЕВАНТНОСТЬ И ОШИБКИ")
    print("=" * 80)
    print()
    
    # Проверяем Women's Health фиды
    print("👩 ПРОВЕРКА WOMEN'S HEALTH RSS ЛЕНТ")
    print("-" * 80)
    
    womens_results = []
    for i, url in enumerate(NEW_WOMENS_FEEDS, 1):
        print(f"[{i}/{len(NEW_WOMENS_FEEDS)}] Проверяю: {url[:60]}...")
        success, result = check_rss_feed(url)
        womens_results.append(result)
        
        if success:
            status_emoji = "✅" if result['relevance_percentage'] >= 60 else "⚠️" if result['relevance_percentage'] >= 40 else "❌"
            print(f"  {status_emoji} Статус: {result['status']} | Статей: {result['articles_count']} | Релевантность: {result['relevance_percentage']}%")
            if result['sample_titles']:
                print(f"  📰 Примеры: {result['sample_titles'][0][:60]}...")
        else:
            print(f"  ❌ Ошибка: {result['error']}")
        
        time.sleep(0.5)  # Небольшая задержка между запросами
    
    print()
    print("👨 ПРОВЕРКА MEN'S HEALTH RSS ЛЕНТ")
    print("-" * 80)
    
    mens_results = []
    for i, url in enumerate(NEW_MENS_FEEDS, 1):
        print(f"[{i}/{len(NEW_MENS_FEEDS)}] Проверяю: {url[:60]}...")
        success, result = check_rss_feed(url)
        mens_results.append(result)
        
        if success:
            status_emoji = "✅" if result['relevance_percentage'] >= 60 else "⚠️" if result['relevance_percentage'] >= 40 else "❌"
            print(f"  {status_emoji} Статус: {result['status']} | Статей: {result['articles_count']} | Релевантность: {result['relevance_percentage']}%")
            if result['sample_titles']:
                print(f"  📰 Примеры: {result['sample_titles'][0][:60]}...")
        else:
            print(f"  ❌ Ошибка: {result['error']}")
        
        time.sleep(0.5)
    
    print()
    print("=" * 80)
    print("📊 ИТОГОВЫЙ ОТЧЁТ")
    print("=" * 80)
    
    # Фильтруем высокорелевантные (>= 60%)
    high_relevance_womens = [r for r in womens_results if r.get('relevance_percentage', 0) >= 60 and r.get('parse_success', False)]
    high_relevance_mens = [r for r in mens_results if r.get('relevance_percentage', 0) >= 60 and r.get('parse_success', False)]
    
    print(f"\n✅ ВЫСОКОРЕЛЕВАНТНЫЕ WOMEN'S HEALTH ({len(high_relevance_womens)}):")
    for r in high_relevance_womens:
        print(f"  • {r['url']} ({r['relevance_percentage']}% релевантность, {r['articles_count']} статей)")
    
    print(f"\n✅ ВЫСОКОРЕЛЕВАНТНЫЕ MEN'S HEALTH ({len(high_relevance_mens)}):")
    for r in high_relevance_mens:
        print(f"  • {r['url']} ({r['relevance_percentage']}% релевантность, {r['articles_count']} статей)")
    
    # Средняя релевантность (40-59%)
    medium_relevance_womens = [r for r in womens_results if 40 <= r.get('relevance_percentage', 0) < 60 and r.get('parse_success', False)]
    medium_relevance_mens = [r for r in mens_results if 40 <= r.get('relevance_percentage', 0) < 60 and r.get('parse_success', False)]
    
    print(f"\n⚠️ СРЕДНЯЯ РЕЛЕВАНТНОСТЬ WOMEN'S HEALTH ({len(medium_relevance_womens)}):")
    for r in medium_relevance_womens:
        print(f"  • {r['url']} ({r['relevance_percentage']}% релевантность)")
    
    print(f"\n⚠️ СРЕДНЯЯ РЕЛЕВАНТНОСТЬ MEN'S HEALTH ({len(medium_relevance_mens)}):")
    for r in medium_relevance_mens:
        print(f"  • {r['url']} ({r['relevance_percentage']}% релевантность)")
    
    # Ошибки
    errors_womens = [r for r in womens_results if not r.get('parse_success', False)]
    errors_mens = [r for r in mens_results if not r.get('parse_success', False)]
    
    if errors_womens:
        print(f"\n❌ ОШИБКИ WOMEN'S HEALTH ({len(errors_womens)}):")
        for r in errors_womens:
            print(f"  • {r['url']} - {r.get('error', 'Unknown error')}")
    
    if errors_mens:
        print(f"\n❌ ОШИБКИ MEN'S HEALTH ({len(errors_mens)}):")
        for r in errors_mens:
            print(f"  • {r['url']} - {r.get('error', 'Unknown error')}")
    
    # Сохраняем результаты
    import json
    with open('new_rss_check_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'womens': womens_results,
            'mens': mens_results,
            'high_relevance_womens': [r['url'] for r in high_relevance_womens],
            'high_relevance_mens': [r['url'] for r in high_relevance_mens],
            'timestamp': datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Результаты сохранены в new_rss_check_results.json")
    print(f"\n✅ Рекомендуется добавить {len(high_relevance_womens) + len(high_relevance_mens)} высокорелевантных RSS лент")

if __name__ == '__main__':
    main()
