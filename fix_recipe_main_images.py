#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Однократное исправление: для 4 опубликованных статей-рецептов ставит первым
изображением фото еды (из галереи), а не тренировки.
Запуск: из каталога fitness-timer-autopost или из корня, где есть public_html/blog-posts.json
"""

import json
import re
from pathlib import Path

# Слаги/подстроки URL статей, которые нужно исправить
RECIPE_SLUGS = [
    "italyanskie-penne-v-multivarke-prostoy-uzhin-dlya",
    "retsept-domashnih-tortilyas-iz-tselnozernovoy-muki",
    "vegetarianskaya-pitstsa-zapekanka-s-nizkoy-kaloriy",
    "lazanya-iz-baklazhanov-v-multivarke-retsept-polezn",
]

# По ним считаем изображение «про еду»
FOOD_KEYWORDS = re.compile(
    r"slow-cooker|crockpot|penne|tortilla|pizza|lasagna|eggplant|recipe|dinner|"
    r"casserole|meal|food|pasta|блюдо|рецепт|ужин|паста|лазанья|пицца|тортильяс|"
    r"баклажан|цельнозернов|мука|запеканка|итальянск",
    re.I
)
# По ним отбрасываем «про тренировки»
FITNESS_KEYWORDS = re.compile(
    r"workout|exercise|yoga|gym|training|тренировк|упражнен|фитнес|pull-?up|"
    r"продукты для фитнеса|питание для тренировок|что есть и когда",
    re.I
)


def is_food_image(url: str, alt: str, title: str) -> bool:
    text = f"{url} {alt} {title}"
    if FITNESS_KEYWORDS.search(text):
        return False
    return bool(FOOD_KEYWORDS.search(text))


def fix_post(post: dict) -> bool:
    url = post.get("url") or ""
    if not any(slug in url for slug in RECIPE_SLUGS):
        return False
    images = post.get("images") or []
    if len(images) < 2:
        return False
    food_idx = None
    for i, img in enumerate(images):
        u = img.get("url") or ""
        a = img.get("alt") or ""
        t = img.get("title") or ""
        if is_food_image(u, a, t):
            food_idx = i
            break
    if food_idx is None:
        return False
    # Ставим выбранное изображение первым
    chosen = dict(images[food_idx])
    chosen["is_main"] = True
    rest = [img for j, img in enumerate(images) if j != food_idx]
    for img in rest:
        img["is_main"] = False
    post["images"] = [chosen] + rest
    post["image"] = chosen.get("url") or post.get("image")
    return True


def main():
    import sys
    if len(sys.argv) > 1:
        blog_posts_path = Path(sys.argv[1]).resolve()
        if not blog_posts_path.exists():
            print(f"❌ Файл не найден: {blog_posts_path}")
            return
    else:
        script_dir = Path(__file__).parent.resolve()
        blog_posts_path = None
        for base in [script_dir.parent, script_dir, Path.cwd()]:
            path = base / "public_html" / "blog-posts.json"
            if path.exists():
                blog_posts_path = path
                break
        if not blog_posts_path:
            print("❌ Файл public_html/blog-posts.json не найден.")
            print("   Укажите путь: python3 fix_recipe_main_images.py <путь к blog-posts.json>")
            print("   Или скачайте с сайта: https://www.tabatatimer.ru/blog-posts.json")
            return
    with open(blog_posts_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    posts = data.get("posts") or []
    fixed = 0
    for post in posts:
        if fix_post(post):
            title = (post.get("title") or "")[:50]
            print(f"✅ Исправлено: {title}…")
            fixed += 1
    if fixed:
        with open(blog_posts_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ В blog-posts.json обновлено главное изображение у {fixed} постов.")
        print("   Дальше запустите: python3 generate_blog_post_page.py")
    else:
        print("ℹ️ Нет постов с указанными слагами или без подходящего фото еды в галерее.")


if __name__ == "__main__":
    main()
