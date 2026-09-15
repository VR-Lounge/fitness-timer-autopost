# -*- coding: utf-8 -*-
"""Фильтры рецептного контента для TABATATIMER: не публикуем рецепты для животных и оффтоп."""

# Подстроки в заголовке/URL (нижний регистр для сравнения)
_BLOCKED_TITLE_OR_URL = (
    'для собак',
    'для кошек',
    'для щенков',
    'для котят',
    'печенье для собак',
    'рецепт для собак',
    'лакомств для собак',
    'dog treat',
    'dog cookie',
    'dog biscuits',
    'homemade dog',
    'pet treat',
    'dog food',
    'puppy treat',
)


def blocked_recipe_not_for_humans(title_ru: str = '', title_en: str = '', url: str = '') -> bool:
    """True — не публиковать в рецептном пайплайне (контент не про еду для людей)."""
    blob = f'{title_ru or ""} {title_en or ""} {url or ""}'.lower()
    return any(s in blob for s in _BLOCKED_TITLE_OR_URL)
