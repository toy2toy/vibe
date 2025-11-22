"""
Seed the SQLite database with AI-generated categories and items.

Usage:
    OPENAI_API_KEY=... python seed_ai.py
    # or use AI_TOKEN env var

Behavior:
- Clears existing items/categories to avoid duplicates.
- Asks ChatGPT for 5 concise category names.
- Asks ChatGPT for 4 items per category with names and reasonable integer prices.
- Generates an icon image per item and saves to frontend/assets/<category-slug>/icon_ai_<item_id>.png
"""

import base64
import json
import os
import time
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

from openai import OpenAI

from main import Base, Category, Item, SessionLocal, engine, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class AIItem:
    name: str
    price: int


def clear_tables(db):
    db.query(Item).delete()
    db.query(Category).delete()
    db.commit()


def get_client():
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_TOKEN")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY or AI_TOKEN is required to seed with ChatGPT.")
    return OpenAI(api_key=api_key)


def prompt_categories(client: OpenAI) -> List[str]:
    system = (
        "You name icon categories for a design catalog. "
        "Return 5 short, distinct category names as a JSON array of strings. "
        "Keep names 1-2 words, no emojis."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
          {"role": "system", "content": system},
          {"role": "user", "content": "Give me 5 concise categories for an icon marketplace."},
        ],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    data = json.loads(content)
    categories = data.get("categories") if isinstance(data, dict) else data
    if not categories or not isinstance(categories, list):
        raise ValueError("Invalid category response")
    return [c.strip() for c in categories if isinstance(c, str) and c.strip()]


def prompt_items(client: OpenAI, category: str) -> List[AIItem]:
    system = (
        "You invent icon names with sensible prices (integer USD). "
        "Respond as JSON array of objects: [{\"name\":\"...\",\"price\":123}]. "
        "Names should be short and human-friendly."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
          {"role": "system", "content": system},
          {"role": "user", "content": f"Give 4 items for the category '{category}'."},
        ],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    data = json.loads(content)
    items = data.get("items") if isinstance(data, dict) else data
    out: List[AIItem] = []
    if not isinstance(items, list):
        raise ValueError(f"Invalid items for {category}")
    for row in items:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        price = row.get("price")
        try:
            price_int = int(price)
        except (TypeError, ValueError):
            continue
        if name and str(name).strip():
            out.append(AIItem(name=str(name).strip(), price=price_int))
    return out


def slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


def generate_item_icon(client: OpenAI, category: str, item: AIItem, dest: Path) -> None:
    """Generate a PNG icon and write it to dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Throttle to avoid image rate limits
        time.sleep(120)
        logger.info("Generating icon for item '%s' in category '%s' -> %s", item.name, category, dest)
        resp = client.images.generate(
            model="dall-e-3",
            prompt=(
                f"Minimal flat vector icon for '{item.name}' in the '{category}' category. "
                "Soft colors, clean lines, no text."
            ),
            size="1024x1024",
            response_format="b64_json",
        )
        image_b64 = resp.data[0].b64_json
        dest.write_bytes(base64.b64decode(image_b64))
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to generate icon for '%s': %s", item.name, exc)


def seed():
    client = get_client()
    init_db()
    Base.metadata.create_all(bind=engine)
    assets_root = Path(__file__).resolve().parent.parent / "frontend" / "assets"
    db = SessionLocal()
    try:
        logger.info("Clearing tables before seeding")
        clear_tables(db)
        categories = prompt_categories(client)[:5]
        for cat_name in categories:
            logger.info("Seeding category '%s'", cat_name)
            cat = Category(name=cat_name, state="online")
            db.add(cat)
            db.flush()
            items = prompt_items(client, cat_name)[:4]
            for item in items:
                record = Item(name=item.name, price=item.price, category_id=cat.id)
                db.add(record)
                db.flush()
                dest = assets_root / slugify(cat_name) / f"icon_ai_{record.id}.png"
                generate_item_icon(client, cat_name, item, dest)
        db.commit()
        logger.info("Seeded %s categories with AI-generated items.", len(categories))
    finally:
        db.close()


if __name__ == "__main__":
    seed()
