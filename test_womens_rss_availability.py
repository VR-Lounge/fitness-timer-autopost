#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки доступности RSS фидов для женского контента
Проверяет доступность и выявляет нерабочие фиды
"""

import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import time

# RSS фиды из womenshealth_parser.py
WOMENSHEALTH_RSS_FEEDS = [
    # ПРИОРИТЕТ 1: ФИТНЕС, HIIT, TABATA, ТРЕНИРОВКИ (1-20)
    'https://hiitscience.com/feed',
    'https://nourishmovelove.com/feed/',
    'https://www.girlsgonestrong.com/feed/',
    'https://gymbunny.ie/feed/',
    'https://www.womenfitness.net/feed/',
    'https://fitnessista.com/feed/',
    'https://femalefitnesssystems.com/feed/',
    'https://fitbottomedgirls.com/feed',
    'https://my.toneitup.com/blogs/latest.atom',
    'https://sarahfit.com/feed/',
    'https://www.fit4females.com/fitblog/feed/',
    'https://healthworksfitness.com/feed/',
    'https://womensfitnessclubs.com/feed/',
    'https://www.fitnessmag.co.za/feed/',
    'https://www.stronghealthywoman.com/feed/',
    'https://www.healthista.com/feed/',
    'https://femmephysiques.com/feed/',
    'https://lazygirlfitness.com.au/feed/',
    'http://fitnessontoast.com/feed/',
    'https://www.kaylainthecity.com/feed/',
    
    # ПРИОРИТЕТ 2: ПИТАНИЕ, ДИЕТЫ, НУТРИЦИОЛОГИЯ (21-29)
    'https://jessicasepel.com/feed',
    'https://www.sheknows.com/health-and-wellness/feed/',
    'https://www.healthywomen.org/feeds/feed.rss',
    'https://nourishinglab.com/feed/',
    'https://www.fempower-health.com/blog-feed.xml',
    'https://realmomnutrition.com/feed',
    'https://abbylangernutrition.com/feed',
    'https://sharonpalmer.com/feed',
    'https://bebodywise.com/blog/rss/',
    
    # ПРИОРИТЕТ 3: МОТИВАЦИЯ + ЛАЙФСТАЙЛ (30-37)
    'http://knocked-upfitness.com/feed/',
    'https://flecksoflex.com/feed/',
    'https://www.jerseygirltalk.com/feed/',
    'https://amodrn.com/feed/',
    'https://www.besthealthmag.ca/wellness/health/feed/',
    'http://www.livingbetter50.com/category/health-fitness/feed/',
    'https://sanitydaily.com/feed/',
    
    # ДОПОЛНИТЕЛЬНЫЕ СПЕЦИАЛИЗИРОВАННЫЕ (38-40)
    'https://bwhi.org/feed/',
    'https://www.intimina.com/blog/feed/',
    'https://www.hormona.io/feed/',
    
    # НОВЫЕ ДОБАВЛЕННЫЕ ФИДЫ
    'https://skinnyms.com/category/fitness/feed/',
    'https://blog.myfitnesspal.com/feed/',
    'https://www.nataliejillfitness.com/feed/',
    'https://lauralondonfitness.com/feed/',
    'https://www.behealthynow.co.uk/feed/',
    'https://hipandhealthy.com/category/fitness/feed/',
    'https://artofhealthyliving.com/category/fitness/feed/',
    'https://www.bornfitness.com/feed/',
    'https://fit4mom.com/blog?format=rss',
    'https://fitgirlsdiary.com/feed/',
    'https://www.healthifyme.com/blog/feed/',
    'https://www.muscleandfitness.com/feed/',
    'https://ellymcguinness.com/feed/',
    'https://www.massyarias.com/feed/',
    'https://www.carlyrowena.com/blog?format=rss',
    'https://barbend.com/feed/',
]

def test_rss_feed(url):
    """Тестирует RSS фид на доступность"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}", None
        
        # Пробуем распарсить XML
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            return False, f"Ошибка парсинга XML: {str(e)[:50]}", None
        
        # Проверяем наличие элементов
        items = []
        if root.tag.endswith('feed'):  # Atom
            items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
        elif root.tag == 'rss':  # RSS 2.0
            channel = root.find('channel')
            if channel is not None:
                items = channel.findall('item')
        
        if not items:
            return False, "Нет статей в фиде", None
        
        return True, f"OK ({len(items)} статей)", len(items)
        
    except requests.exceptions.Timeout:
        return False, "Timeout (>15 сек)", None
    except requests.exceptions.SSLError:
        return False, "SSL ошибка", None
    except requests.exceptions.ConnectionError:
        return False, "Ошибка подключения", None
    except requests.exceptions.RequestException as e:
        return False, f"Ошибка запроса: {str(e)[:50]}", None
    except Exception as e:
        return False, f"Неожиданная ошибка: {str(e)[:50]}", None

def main():
    """Основная функция тестирования"""
    print("="*70)
    print("ПРОВЕРКА ДОСТУПНОСТИ RSS ФИДОВ ДЛЯ ЖЕНСКОГО КОНТЕНТА")
    print("="*70)
    print()
    
    working_feeds = []
    failed_feeds = []
    
    for i, url in enumerate(WOMENSHEALTH_RSS_FEEDS, 1):
        print(f"[{i}/{len(WOMENSHEALTH_RSS_FEEDS)}] Проверка: {url[:60]}...", end=' ', flush=True)
        
        is_working, status, articles_count = test_rss_feed(url)
        
        if is_working:
            print(f"✅ {status}")
            working_feeds.append((url, articles_count))
        else:
            print(f"❌ {status}")
            failed_feeds.append((url, status))
        
        # Небольшая пауза между запросами
        time.sleep(0.5)
    
    # Итоговый отчет
    print()
    print("="*70)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*70)
    print(f"\n✅ Рабочих фидов: {len(working_feeds)} ({len(working_feeds)/len(WOMENSHEALTH_RSS_FEEDS)*100:.1f}%)")
    print(f"❌ Нерабочих фидов: {len(failed_feeds)} ({len(failed_feeds)/len(WOMENSHEALTH_RSS_FEEDS)*100:.1f}%)")
    
    if working_feeds:
        print(f"\n✅ РАБОЧИЕ ФИДЫ ({len(working_feeds)}):")
        for url, count in sorted(working_feeds, key=lambda x: x[1] or 0, reverse=True):
            print(f"   ✅ {url} ({count or '?'} статей)")
    
    if failed_feeds:
        print(f"\n❌ НЕРАБОТАЮЩИЕ ФИДЫ ({len(failed_feeds)}):")
        for url, error in failed_feeds:
            print(f"   ❌ {url}")
            print(f"      Ошибка: {error}")
    
    print()
    print("="*70)
    print("РЕКОМЕНДАЦИИ")
    print("="*70)
    if len(failed_feeds) > len(working_feeds) * 0.3:  # Если больше 30% нерабочих
        print("⚠️ КРИТИЧНО: Более 30% фидов не работают!")
        print("   Рекомендуется:")
        print("   1. Удалить нерабочие фиды из списка")
        print("   2. Добавить новые рабочие источники")
        print("   3. Проверить настройки User-Agent и timeout")
    else:
        print("✅ Большинство фидов работают нормально")
        if failed_feeds:
            print("   Рекомендуется удалить нерабочие фиды для оптимизации")

if __name__ == '__main__':
    main()
