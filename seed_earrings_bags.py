import re
import html
import json
from db import SessionLocal, Asset, init_db

earrings_html = """<div class="option-modal__grid"><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                ring-brand-1000 ring-3"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="1" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_earring_product_01_41c943f9fc.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="2" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_earring_product_02_b38dc58c4a.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="3" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_earring_product_03_f46ee285fc.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="4" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_earring_product_04_494990c913.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="5" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_earring_product_05_76fa37da3c.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="6" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_earring_product_06_f258e4765b.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="7" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_earring_product_07_5476e0a156.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="8" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_earring_product_08_342281c7f1.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="9" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_earring_product_09_52ac60c037.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="10" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_earring_product_10_308996c245.png"></div></div></div>"""

bags_html = """<div class="option-modal__grid"><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                ring-brand-1000 ring-3"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="1" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Bag_1_32e7073034.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="2" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Bag_2_b85d1386b5.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="3" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Bag_3_3d21a877a2.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="4" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Bag_4_eec5bf50b4.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="5" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Bag_5_773888af29.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="6" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Bag_6_af3913a5ce.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="7" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Bag_7_fcce3fd84b.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="8" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Bag_8_c05f979a9f.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="9" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Bag_9_c7e86fb5ae.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="10" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Bag_10_a084060bcf.jpg"></div></div></div>"""

def parse_items(text, category, names):
    pattern = re.compile(r'<img[^>]+alt="([^"]+)"[^>]+src="([^"]+)"', re.IGNORECASE)
    matches = pattern.findall(text)
    items = []
    for idx, (alt, src) in enumerate(matches, 1):
        name = names[idx - 1] if idx <= len(names) else f"{category.title()} #{idx}"
        items.append({
            "id_num": idx,
            "name": name,
            "tag": f"{category}-{idx}",
            "url": src.strip(),
            "category": category
        })
    return items

earring_names = [
    "Pavé Diamond Huggies",
    "Classic Pearl Studs",
    "Emerald Drop Earrings",
    "Modern Gold Hoops",
    "Sapphire Crystal Cascades",
    "Rose Gold Teardrops",
    "Chic Geometric Dangles",
    "Vintage Chandelier Drops",
    "Minimalist Bar Studs",
    "Solitaire Diamond Studs"
]

bag_names = [
    "Parisian Leather Crossbody",
    "Classic Quilted Shoulder Bag",
    "Structured Saffiano Tote",
    "Velvet Evening Clutch",
    "Cognac Saddle Bag",
    "Minimalist Hobo Bag",
    "Monogram Canvas Satchel",
    "Woven Straw Beach Tote",
    "Urban Camera Bag",
    "Midnight Croc-Embossed Bag"
]

earrings = parse_items(earrings_html, "earring", earring_names)
bags = parse_items(bags_html, "bag", bag_names)

with open("earrings_data.json", "w", encoding="utf-8") as f:
    json.dump(earrings, f, indent=2, ensure_ascii=False)

with open("bags_data.json", "w", encoding="utf-8") as f:
    json.dump(bags, f, indent=2, ensure_ascii=False)

print(f"Extracted {len(earrings)} earrings and {len(bags)} bags.")

init_db()
db = SessionLocal()
try:
    for item_list in [earrings, bags]:
        inserted = 0
        updated = 0
        cat = item_list[0]["category"]
        for item in item_list:
            url = item["url"]
            name = item["name"]
            key = f"cdn_{cat}_{item['id_num']}"
            meta = json.dumps({"pattern_id": item["id_num"], "tag": item["tag"]})

            existing = db.query(Asset).filter(
                Asset.category == cat,
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
                    category=cat,
                    name=name,
                    b2_key=key,
                    b2_url=url,
                    thumbnail_url=url,
                    meta_json=meta
                )
                db.add(new_asset)
                inserted += 1
        db.commit()
        total = db.query(Asset).filter(Asset.category == cat).count()
        print(f"Sync {cat}: {inserted} inserted, {updated} updated. Total in DB: {total}")
finally:
    db.close()
