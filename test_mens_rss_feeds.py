#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для тестирования мужских RSS фидов
Проверяет доступность и релевантность RSS каналов
"""

import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import time

# Новые мужские RSS фиды для тестирования
NEW_MENS_RSS_FEEDS = [
    # ТОП-ПРИОРИТЕТ
    ("Men's Health (USA)", "https://www.menshealth.com/rss/fitness.xml"),
    ("Muscle & Fitness", "https://www.muscleandfitness.com/feed/"),
    ("Muscle & Strength", "https://www.muscleandstrength.com/rss.xml"),
    ("Nerd Fitness", "https://www.nerdfitness.com/feed/"),
    ("BarBend", "https://barbend.com/feed/"),
    
    # HIIT, TABATA, EMOM, AMRAP
    ("HIIT Science", "https://hiitscience.com/feed"),
    ("Men's Fitness", "https://www.mensfitness.com/.rss/feed/5a4c1162-86c8-4b99-8611-d683873db65d.xml"),
    ("Ross Training", "https://rosstraining.com/blog/feed/"),
    
    # СИЛОВЫЕ ТРЕНИРОВКИ
    ("StrongFirst", "https://strongfirst.com/blog/feed"),
    ("Starting Strength", "https://startingstrength.com/rss.rss"),
    ("Breaking Muscle", "https://breakingmuscle.com/feed/"),
    ("Tony Gentilcore", "https://tonygentilcore.com/feed/"),
    ("Dr. John Rusin", "https://drjohnrusin.com/feed/"),
    ("Volt Athletics Blog", "https://feeds.feedburner.com/volt-blog"),
    
    # ФУНКЦИОНАЛЬНЫЙ ФИТНЕС
    ("Fit Dad Chris", "https://fitdadchris.com/feed/"),
    ("Hard To Kill Fitness", "https://hardtokillfitness.co/blogs/fitness-articles.atom"),
    ("Train Heroic", "https://www.trainheroic.com/feed/"),
    ("Simpli Faster", "https://simplifaster.com/articles/category/blog/feed/"),
    
    # ПИТАНИЕ + БИОХАКИНГ
    ("Ben Greenfield Life", "https://bengreenfieldlife.com/article/feed/"),
    ("Born Fitness", "https://www.bornfitness.com/feed/"),
    
    # КОМЬЮНИТИ + ЛАЙФСТАЙЛ
    ("MensFitClub.com", "https://www.mensfitclub.com/mens-fitness/feed/"),
    ("Active Man", "https://activeman.com/category/health-fitness/feed/"),
    ("Zen Habits", "https://zenhabits.net/feed/"),
    ("Dai Manuel", "https://www.daimanuel.com/feed"),
    
    # СПЕЦИАЛИЗИРОВАННЫЕ
    ("Focus Fitness", "https://www.focusfitness.in/feed/"),
]

# Ключевые слова для проверки релевантности (мужская аудитория)
RELEVANT_KEYWORDS = [
    'tabata', 'hiit', 'emom', 'amrap', 'interval', 'circuit', 'workout',
    'strength training', 'muscle building', 'workout for men', 'dad fitness',
    'testosterone', 'protein', 'fat loss', 'six pack', 'functional fitness',
    'crossfit', 'bodybuilding', 'powerlifting', 'weightlifting', 'training',
    'exercise', 'fitness', 'nutrition', 'diet', 'supplements', 'recovery',
    'men health', 'male fitness', 'gym', 'training program', 'workout plan'
]

def test_rss_feed(name, url):
    """Тестирует RSS фид на доступность и релевантность"""
    print(f"\n{'='*60}")
    print(f"Тестирование: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        # Проверяем доступность
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Ошибка: HTTP {response.status_code}")
            return False, None
        
        # Парсим XML
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            print(f"❌ Ошибка парсинга XML: {e}")
            return False, None
        
        # Проверяем наличие элементов
        items = []
        if root.tag.endswith('feed'):  # Atom
            items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
        elif root.tag == 'rss':  # RSS 2.0
            channel = root.find('channel')
            if channel is not None:
                items = channel.findall('item')
        
        if not items:
            print(f"❌ Не найдено статей в фиде")
            return False, None
        
        print(f"✅ Найдено статей: {len(items)}")
        
        # Проверяем релевантность (первые 5 статей)
        relevant_count = 0
        sample_titles = []
        
        for item in items[:5]:
            title = ''
            description = ''
            
            if item.tag.endswith('entry'):  # Atom
                title_elem = item.find('.//{http://www.w3.org/2005/Atom}title')
                summary_elem = item.find('.//{http://www.w3.org/2005/Atom}summary')
                if title_elem is not None:
                    title = title_elem.text or ''
                if summary_elem is not None:
                    description = summary_elem.text or ''
            else:  # RSS 2.0
                title_elem = item.find('title')
                desc_elem = item.find('description')
                if title_elem is not None:
                    title = title_elem.text or ''
                if desc_elem is not None:
                    description = desc_elem.text or ''
            
            text = (title + ' ' + description).lower()
            
            # Проверяем наличие ключевых слов
            is_relevant = any(keyword in text for keyword in RELEVANT_KEYWORDS)
            
            if is_relevant:
                relevant_count += 1
                sample_titles.append(title[:60])
        
        relevance_percent = (relevant_count / min(5, len(items))) * 100
        print(f"✅ Релевантность: {relevant_count}/{min(5, len(items))} статей ({relevance_percent:.0f}%)")
        
        if sample_titles:
            print(f"📝 Примеры статей:")
            for t in sample_titles[:3]:
                print(f"   - {t}")
        
        # Считаем релевантным, если хотя бы 40% статей релевантны
        is_relevant = relevance_percent >= 40
        
        return is_relevant, {
            'name': name,
            'url': url,
            'articles_count': len(items),
            'relevance': relevance_percent
        }
        
    except requests.exceptions.Timeout:
        print(f"❌ Таймаут при загрузке")
        return False, None
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return False, None
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False, None

def main():
    """Основная функция тестирования"""
    print("="*60)
    print("ТЕСТИРОВАНИЕ МУЖСКИХ RSS ФИДОВ")
    print("="*60)
    
    working_feeds = []
    failed_feeds = []
    
    for name, url in NEW_MENS_RSS_FEEDS:
        is_working, info = test_rss_feed(name, url)
        
        if is_working and info:
            working_feeds.append(info)
        else:
            failed_feeds.append((name, url))
        
        # Небольшая пауза между запросами
        time.sleep(1)
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)
    print(f"\n✅ Рабочих фидов: {len(working_feeds)}")
    print(f"❌ Не рабочих фидов: {len(failed_feeds)}")
    
    if working_feeds:
        print("\n📋 РАБОЧИЕ ФИДЫ (для добавления в парсер):")
        print("\nMENSHEALTH_RSS_FEEDS = [")
        for feed in sorted(working_feeds, key=lambda x: x['relevance'], reverse=True):
            print(f"    # {feed['name']} ({feed['relevance']:.0f}% релевантность, {feed['articles_count']} статей)")
            print(f"    '{feed['url']}',")
        print("]")
    
    if failed_feeds:
        print("\n❌ НЕ РАБОТАЮЩИЕ ФИДЫ:")
        for name, url in failed_feeds:
            print(f"   - {name}: {url}")

if __name__ == '__main__':
    main()
