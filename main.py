"""
FastAPI application entry point.
Run: uvicorn main:app --reload --port 8000
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from db import init_db, SessionLocal, User
from auth import hash_password

# Load .env
load_dotenv()

# ─── Routers ──────────────────────────────────────────────────────────────────
from modules.home        import router as home_router
from modules.auth_router import router as auth_router
from modules.skin        import router as skin_router
from modules.palette     import router as palette_router
from modules.hair        import router as hair_router
from modules.eyes        import router as eyes_router
from modules.style       import router as style_router
from modules.history     import router as history_router
from modules.admin       import router as admin_router
from modules.brand       import router as brand_router

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("styleai")

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="StyleAI Studio", version="1.0.0")

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Incoming {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Completed {request.method} {request.url.path} -> {response.status_code}")
    return response

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "styleai-dev-secret-change-in-prod"),
    max_age=86_400 * 30,  # 30-day sessions
)

# Static files
_BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(_BASE / "static" / "img" / "favicon.ico")

@app.get("/health", tags=["system"])
@app.get("/healthz", tags=["system"])
async def health_check():
    """Liveness probe for Render and orchestrators."""
    return {"status": "healthy", "service": "styleai-studio", "version": "1.0.0"}

# Routers
app.include_router(home_router)
app.include_router(auth_router,     prefix="/auth")
app.include_router(skin_router,     prefix="/skin",     tags=["skin"])
app.include_router(palette_router,  prefix="/palette",  tags=["palette"])
app.include_router(hair_router,     prefix="/hair",     tags=["hair"])
app.include_router(eyes_router,     prefix="/eyes",     tags=["eyes"])
app.include_router(style_router,    prefix="/style",    tags=["style"])
app.include_router(brand_router,    prefix="/brand",    tags=["brand"])
app.include_router(history_router)
app.include_router(admin_router,    prefix="/admin",    tags=["admin"])


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    _seed_users()
    _seed_hairstyles()
    _seed_eye_lenses()
    _seed_clothes_and_shoes()
    _seed_necklaces()
    _seed_earrings_and_bags()
    _seed_brand_assets()


def _seed_brand_assets():
    """Seed full-body standing preset models and isolated brand garments for neural fitting testing."""
    from db import BrandModel, BrandProduct
    db = SessionLocal()
    try:
        model_data = [
            {
                "name": "Elena Rostova",
                "gender": "Female",
                "undertone": "Warm Golden",
                "height": "5'10 / 178cm",
                "notes": "Full-body high-fashion runway & editorial casting model. Optimal with Warm & Earthy tones.",
                "b2_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=800&q=80",
                "is_preset": True,
            },
            {
                "name": "Sophia Laurent",
                "gender": "Female",
                "undertone": "Cool Rose",
                "height": "5'9 / 175cm",
                "notes": "Full-body haute couture eveningwear & catalog model. Flattering with Navy, Emerald & Jewel tones.",
                "b2_url": "https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=800&q=80",
                "is_preset": True,
            },
            {
                "name": "Aaliyah Vance",
                "gender": "Female",
                "undertone": "Deep Espresso",
                "height": "5'11 / 180cm",
                "notes": "Full-body contemporary ready-to-wear & activewear talent. Highly versatile color harmony.",
                "b2_url": "https://images.unsplash.com/photo-1581044777550-4cfa60707c03?auto=format&fit=crop&w=800&q=80",
                "is_preset": True,
            },
            {
                "name": "Maya Chen",
                "gender": "Female",
                "undertone": "Fair Peach",
                "height": "5'10 / 177cm",
                "notes": "Full-body minimalist editorial model. Radiant in Camel, Ivory, Sand & Pastel tones.",
                "b2_url": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?auto=format&fit=crop&w=800&q=80",
                "is_preset": True,
            },
            {
                "name": "Marcus Sterling",
                "gender": "Male",
                "undertone": "Warm Bronze",
                "height": "6'2 / 188cm",
                "notes": "Full-body luxury menswear & outerwear model. Ideal for Tailored blazers & Camel coats.",
                "b2_url": "https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=800&q=80",
                "is_preset": True,
            },
            {
                "name": "Jordan Reed",
                "gender": "Male",
                "undertone": "Deep Espresso",
                "height": "6'1 / 185cm",
                "notes": "Full-body menswear & formal suit specialist. Striking contrast in Bold Jewel & Crisp Tones.",
                "b2_url": "https://images.unsplash.com/photo-1552374196-1ab2a1c593e8?auto=format&fit=crop&w=800&q=80",
                "is_preset": True,
            },
            {
                "name": "David Becker",
                "gender": "Male",
                "undertone": "Cool Fair",
                "height": "6'1 / 186cm",
                "notes": "Full-body modern tailoring & classic menswear casting favorite.",
                "b2_url": "https://images.unsplash.com/photo-1534030347209-467a5b0ad3e6?auto=format&fit=crop&w=800&q=80",
                "is_preset": True,
            },
            {
                "name": "Liam Tanaka",
                "gender": "Male",
                "undertone": "Neutral Slate",
                "height": "6'0 / 183cm",
                "notes": "Full-body ready-to-wear streetwear & contemporary urban menswear talent.",
                "b2_url": "https://images.unsplash.com/photo-1488161628813-04466f872be2?auto=format&fit=crop&w=800&q=80",
                "is_preset": True,
            },
        ]

        # Reset preset models cleanly (keep non-preset custom user uploads)
        db.query(BrandModel).filter(BrandModel.is_preset == True).delete()
        for md in model_data:
            db.add(BrandModel(**md))
        db.commit()

        # Clean isolated garment products for Neural Cloth-v4 Try-On
        product_data = [
            {
                "title": "Haute Couture Silk Evening Gown",
                "sku": "FW26-DR-001",
                "category": "dress",
                "color": "Champagne Rose",
                "description": "Floor-length satin couture gown with structured bodice and silk drape.",
                "b2_url": "https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_01_8190f45a28.png",
                "is_preset": True,
            },
            {
                "title": "Pleated Crepe Summer Midi Dress",
                "sku": "FW26-DR-002",
                "category": "dress",
                "color": "Emerald Green",
                "description": "Lustrous emerald pleated dress with bias drape and waist cinch.",
                "b2_url": "https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_02_e8b9d78f2e.png",
                "is_preset": True,
            },
            {
                "title": "Structured Tailored Wool Blazer",
                "sku": "FW26-TP-014",
                "category": "top",
                "color": "Navy Charcoal",
                "description": "Structured single-breasted wool blend tailored executive blazer.",
                "b2_url": "https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_01_3f376bb653.png",
                "is_preset": True,
            },
            {
                "title": "Minimalist Oversized Poplin Shirt",
                "sku": "FW26-TP-015",
                "category": "top",
                "color": "Crisp White",
                "description": "Relaxed-fit crisp cotton poplin shirt with point collar.",
                "b2_url": "https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_02_f9c20f7e80.png",
                "is_preset": True,
            },
            {
                "title": "Classic Double-Breasted Trench Coat",
                "sku": "FW26-CO-088",
                "category": "outerwear",
                "color": "Warm Camel",
                "description": "Classic belted trench overcoat with storm flap and wide notched lapels.",
                "b2_url": "https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_02_f08cb507ce.png",
                "is_preset": True,
            },
            {
                "title": "Cashmere Belted Wrap Overcoat",
                "sku": "FW26-CO-089",
                "category": "outerwear",
                "color": "Midnight Black",
                "description": "Luxury cashmere blend belted wrap coat with deep patch pockets.",
                "b2_url": "https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_016_364e8d57e5.png",
                "is_preset": True,
            },
            {
                "title": "Tailored Pleated Tapered Trousers",
                "sku": "FW26-PT-033",
                "category": "bottom",
                "color": "Slate Grey",
                "description": "High-rise tailored trousers with double pleats and tapered cuffs.",
                "b2_url": "https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_01_6a2df013ca.png",
                "is_preset": True,
            },
            {
                "title": "High-Waist Wide Leg Crepe Pants",
                "sku": "FW26-PT-034",
                "category": "bottom",
                "color": "Ivory Cream",
                "description": "Fluid wide-leg crepe trousers with clean waistband and elegant drape.",
                "b2_url": "https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_02_f3cbaace57.png",
                "is_preset": True,
            },
        ]

        # Reset preset products cleanly (keep non-preset custom user uploads)
        db.query(BrandProduct).filter(BrandProduct.is_preset == True).delete()
        for pd in product_data:
            db.add(BrandProduct(**pd))
        db.commit()

    except Exception as e:
        logger.warning(f"Error seeding brand assets: {e}")
    finally:
        db.close()


def _seed_hairstyles():
    """Seed comprehensive hairstyles catalog using direct CDN links without re-downloading/uploading."""
    from db import Asset
    import json
    from pathlib import Path

    db = SessionLocal()
    try:
        json_path = Path(__file__).parent / "hairstyles_data.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                hair_list = json.load(f)

            existing_urls = {
                a[0] for a in db.query(Asset.b2_url).filter(Asset.category == "hairstyle").all()
            }

            new_assets = []
            for idx, item in enumerate(hair_list):
                url = item.get("url")
                if url and url not in existing_urls:
                    name = item.get("name", "Hairstyle")
                    gender = item.get("gender", "Women / General")
                    meta = json.dumps({"gender": gender, "collection": "women" if "Women" in gender else "men"})
                    slug = name.lower().replace(" ", "_").replace("&", "and")
                    new_assets.append(
                        Asset(
                            category="hairstyle",
                            name=name,
                            b2_key=f"cdn_hair_{idx+1}_{slug}",
                            b2_url=url,
                            thumbnail_url=url,
                            meta_json=meta,
                        )
                    )
                    existing_urls.add(url)

            if new_assets:
                db.add_all(new_assets)
                db.commit()
                logger.info(f"Seeded {len(new_assets)} new hairstyles into database.")
    except Exception as e:
        logger.warning(f"Error seeding hairstyles: {e}")
    finally:
        db.close()


def _seed_eye_lenses():
    """Seed comprehensive eye lens catalog using direct CDN links."""
    from db import Asset
    import json
    from pathlib import Path

    db = SessionLocal()
    try:
        json_path = Path(__file__).parent / "eyelens_data.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                lens_list = json.load(f)

            existing_urls = {
                a[0] for a in db.query(Asset.b2_url).filter(Asset.category == "lens").all()
            }

            new_assets = []
            for item in lens_list:
                url = item.get("url")
                if url and url not in existing_urls:
                    name = item.get("name", "Eye Lens")
                    key = f"cdn_lens_{item.get('id_num', 1)}"
                    meta = json.dumps({"tone": item.get("tone", ""), "pattern_id": item.get("id_num", 1)})
                    new_assets.append(
                        Asset(
                            category="lens",
                            name=name,
                            b2_key=key,
                            b2_url=url,
                            thumbnail_url=url,
                            meta_json=meta,
                        )
                    )
                    existing_urls.add(url)

            if new_assets:
                db.add_all(new_assets)
                db.commit()
                logger.info(f"Seeded {len(new_assets)} new eye lenses into database.")
    except Exception as e:
        logger.warning(f"Error seeding eye lenses: {e}")
    finally:
        db.close()


def _seed_clothes_and_shoes():
    """Seed comprehensive clothes & shoes catalog using direct CDN links."""
    from db import Asset
    import json
    from pathlib import Path

    db = SessionLocal()
    try:
        json_path = Path(__file__).parent / "clothes_shoes_data.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                item_list = json.load(f)

            existing_urls = {
                a[0] for a in db.query(Asset.b2_url).filter(Asset.category.in_(["garment", "shoes"])).all()
            }

            new_assets = []
            for item in item_list:
                url = item.get("url")
                if url and url not in existing_urls:
                    name = item.get("name", "Fashion Item")
                    cat = item.get("category", "garment")
                    subcat = item.get("subcategory", "full_body")
                    tag = item.get("tag", "")
                    key = f"cdn_{cat}_{tag.replace('-', '_')}"
                    meta = json.dumps({"subcategory": subcat, "tag": tag})
                    new_assets.append(
                        Asset(
                            category=cat,
                            name=name,
                            b2_key=key,
                            b2_url=url,
                            thumbnail_url=url,
                            meta_json=meta,
                        )
                    )
                    existing_urls.add(url)

            if new_assets:
                db.add_all(new_assets)
                db.commit()
                logger.info(f"Seeded {len(new_assets)} new clothes and shoes into database.")
    except Exception as e:
        logger.warning(f"Error seeding clothes and shoes: {e}")
    finally:
        db.close()


def _seed_necklaces():
    """Seed necklace catalog using direct CDN links."""
    from db import Asset
    import json
    from pathlib import Path

    db = SessionLocal()
    try:
        json_path = Path(__file__).parent / "necklaces_data.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                item_list = json.load(f)

            existing_urls = {
                a[0] for a in db.query(Asset.b2_url).filter(Asset.category == "necklace").all()
            }

            new_assets = []
            for item in item_list:
                url = item.get("url")
                if url and url not in existing_urls:
                    name = item.get("name", "Necklace")
                    tag = item.get("tag", "")
                    key = f"cdn_necklace_{item.get('id_num', 1)}"
                    meta = json.dumps({"pattern_id": item.get("id_num", 1), "tag": tag})
                    new_assets.append(
                        Asset(
                            category="necklace",
                            name=name,
                            b2_key=key,
                            b2_url=url,
                            thumbnail_url=url,
                            meta_json=meta,
                        )
                    )
                    existing_urls.add(url)

            if new_assets:
                db.add_all(new_assets)
                db.commit()
                logger.info(f"Seeded {len(new_assets)} new necklaces into database.")
    except Exception as e:
        logger.warning(f"Error seeding necklaces: {e}")
    finally:
        db.close()


def _seed_earrings_and_bags():
    """Seed earrings and luxury bags catalog using direct CDN links."""
    from db import Asset
    import json
    from pathlib import Path

    db = SessionLocal()
    try:
        for json_name, cat in [("earrings_data.json", "earring"), ("bags_data.json", "bag")]:
            json_path = Path(__file__).parent / json_name
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    item_list = json.load(f)

                existing_urls = {
                    a[0] for a in db.query(Asset.b2_url).filter(Asset.category == cat).all()
                }

                new_assets = []
                for item in item_list:
                    url = item.get("url")
                    if url and url not in existing_urls:
                        name = item.get("name", cat.title())
                        tag = item.get("tag", "")
                        key = f"cdn_{cat}_{item.get('id_num', 1)}"
                        meta = json.dumps({"pattern_id": item.get("id_num", 1), "tag": tag})
                        new_assets.append(
                            Asset(
                                category=cat,
                                name=name,
                                b2_key=key,
                                b2_url=url,
                                thumbnail_url=url,
                                meta_json=meta,
                            )
                        )
                        existing_urls.add(url)

                if new_assets:
                    db.add_all(new_assets)
                    db.commit()
                    logger.info(f"Seeded {len(new_assets)} new {cat}s into database.")
    except Exception as e:
        logger.warning(f"Error seeding earrings/bags: {e}")
    finally:
        db.close()


def _seed_users():
    """Create demo + admin accounts on first boot."""
    db = SessionLocal()
    try:
        demo_pwd  = os.getenv("DEMO_PASSWORD",  "demo1234")
        admin_pwd = os.getenv("ADMIN_PASSWORD", "admin_secret")

        if not db.query(User).filter(User.email == "demo@styleai.com").first():
            db.add(User(
                username="demo_user",
                email="demo@styleai.com",
                password_hash=hash_password(demo_pwd),
                is_guest=False,
                is_admin=False,
            ))

        if not db.query(User).filter(User.email == "admin@styleai.com").first():
            db.add(User(
                username="admin",
                email="admin@styleai.com",
                password_hash=hash_password(admin_pwd),
                is_guest=False,
                is_admin=True,
            ))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
