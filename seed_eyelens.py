import json
from db import SessionLocal, Asset, init_db

lenses = [
    {
        "id_num": 1,
        "name": "Lens 01 — Hazel Amber",
        "url": "https://plugins-media.makeupar.com/strapi/assets/webp_eye_len_01_788c0418fe.png",
        "tone": "Warm Amber"
    },
    {
        "id_num": 2,
        "name": "Lens 02 — Honey Gold",
        "url": "https://plugins-media.makeupar.com/strapi/assets/webp_eye_len_02_923bbe3775.png",
        "tone": "Honey Gold"
    },
    {
        "id_num": 3,
        "name": "Lens 03 — Mystic Gray",
        "url": "https://plugins-media.makeupar.com/strapi/assets/webp_eye_len_03_37e6555083.png",
        "tone": "Cool Slate"
    },
    {
        "id_num": 4,
        "name": "Lens 04 — Aqua Blue",
        "url": "https://plugins-media.makeupar.com/strapi/assets/webp_eye_len_04_2b844f6473.png",
        "tone": "Vibrant Aqua"
    },
    {
        "id_num": 5,
        "name": "Lens 05 — Emerald Crystal",
        "url": "https://plugins-media.makeupar.com/strapi/assets/webp_eye_len_05_a2cb4f207a.png",
        "tone": "Emerald Green"
    },
    {
        "id_num": 6,
        "name": "Lens 06 — Sapphire Sparkle",
        "url": "https://plugins-media.makeupar.com/strapi/assets/webp_eye_len_06_a6bc280531.png",
        "tone": "Deep Sapphire"
    },
    {
        "id_num": 7,
        "name": "Lens 07 — Deep Violet",
        "url": "https://plugins-media.makeupar.com/strapi/assets/webp_eye_len_07_7f51dcb1c4.png",
        "tone": "Amethyst Violet"
    },
    {
        "id_num": 8,
        "name": "Lens 08 — Smoky Quartz",
        "url": "https://plugins-media.makeupar.com/strapi/assets/webp_eye_len_08_ba64f9a483.png",
        "tone": "Smoky Quartz"
    },
    {
        "id_num": 9,
        "name": "Lens 09 — Olive Green",
        "url": "https://plugins-media.makeupar.com/strapi/assets/webp_eye_len_09_2fca0cf739.png",
        "tone": "Natural Olive"
    },
    {
        "id_num": 10,
        "name": "Lens 10 — Platinum Iris",
        "url": "https://plugins-media.makeupar.com/strapi/assets/webp_eye_len_10_3015d30b1c.png",
        "tone": "Platinum Silver"
    }
]

# Save dataset to json
with open("eyelens_data.json", "w", encoding="utf-8") as f:
    json.dump(lenses, f, indent=2, ensure_ascii=False)

print(f"Saved {len(lenses)} lenses to eyelens_data.json")

# Sync to DB
init_db()
db = SessionLocal()
try:
    inserted = 0
    updated = 0

    for item in lenses:
        url = item["url"]
        name = item["name"]
        key = f"cdn_lens_{item['id_num']}"
        meta = json.dumps({"tone": item["tone"], "pattern_id": item["id_num"]})

        existing = db.query(Asset).filter(
            Asset.category == "lens",
            (Asset.b2_url == url) | (Asset.b2_key == key)
        ).first()

        if existing:
            existing.name = name
            existing.b2_url = url
            existing.thumbnail_url = url
            existing.meta_json = meta
            updated += 1
        else:
            new_asset = Asset(
                category="lens",
                name=name,
                b2_key=key,
                b2_url=url,
                thumbnail_url=url,
                meta_json=meta
            )
            db.add(new_asset)
            inserted += 1

    db.commit()
    print(f"Lens Sync complete: {inserted} inserted, {updated} updated.")
    total_lenses = db.query(Asset).filter(Asset.category == "lens").count()
    print(f"Total lenses in DB: {total_lenses}")

finally:
    db.close()
