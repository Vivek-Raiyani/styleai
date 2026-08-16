import re
import html
import json
from db import SessionLocal, Asset, init_db

raw_html = """<div class="option-modal__grid"><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                ring-brand-1000 ring-3"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="1" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_necklace_product_01_124206cfbe.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="2" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_necklace_product_02_d3c1f00fb3.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="3" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_necklace_product_03_c1e5aa5544.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="4" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_necklace_product_04_af8019c120.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="5" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_necklace_product_05_6c50ea5f44.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="6" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_necklace_product_06_661e26e298.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="7" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_necklace_product_07_a9228aeed0.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="8" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_necklace_product_08_0e12d140a9.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="9" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_necklace_product_09_cc8e107d00.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="10" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_necklace_product_10_9de7c70ccb.png"></div></div></div>"""

def parse_necklaces(text):
    pattern = re.compile(r'<img[^>]+alt="([^"]+)"[^>]+src="([^"]+)"', re.IGNORECASE)
    matches = pattern.findall(text)
    items = []
    names = [
        "Diamond Solitaire Pendant",
        "Classic Pearl Choker",
        "Layered Gold Chain",
        "Emerald Teardrop Necklace",
        "Modern Geometric Collar",
        "Rose Gold Heart Locket",
        "Sapphire Halo Pendant",
        "Vintage Filigree Chain",
        "Minimalist Bar Necklace",
        "Pavé Crystal Statement Piece",
    ]
    for idx, (alt, src) in enumerate(matches, 1):
        name = names[idx - 1] if idx <= len(names) else f"Necklace Piece #{idx}"
        items.append({
            "id_num": idx,
            "name": name,
            "tag": f"necklace-{idx}",
            "url": src.strip(),
            "category": "necklace"
        })
    return items

necklaces = parse_necklaces(raw_html)
print(f"Extracted {len(necklaces)} necklaces.")

with open("necklaces_data.json", "w", encoding="utf-8") as f:
    json.dump(necklaces, f, indent=2, ensure_ascii=False)
print("Saved to necklaces_data.json")

init_db()
db = SessionLocal()
try:
    inserted = 0
    updated = 0
    for item in necklaces:
        url = item["url"]
        name = item["name"]
        key = f"cdn_necklace_{item['id_num']}"
        meta = json.dumps({"pattern_id": item["id_num"], "tag": item["tag"]})

        existing = db.query(Asset).filter(
            Asset.category == "necklace",
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
                category="necklace",
                name=name,
                b2_key=key,
                b2_url=url,
                thumbnail_url=url,
                meta_json=meta
            )
            db.add(new_asset)
            inserted += 1

    db.commit()
    print(f"Sync complete: {inserted} inserted, {updated} updated.")
    total = db.query(Asset).filter(Asset.category == "necklace").count()
    print(f"Total necklaces in DB: {total}")
finally:
    db.close()
