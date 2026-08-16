"""
Database models and session factory — SQLite (hackathon), Postgres-ready schema.
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, Text, ForeignKey, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./styleai.db")
# Render provides postgres:// urls, but SQLAlchemy 2.0 requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(64), unique=True, index=True, nullable=False)
    email         = Column(String(254), unique=True, index=True, nullable=True)
    password_hash = Column(String(256), nullable=True)   # null for guests
    is_guest      = Column(Boolean, default=False, nullable=False)
    is_admin      = Column(Boolean, default=False, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    selfies = relationship("Selfie", back_populates="user", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="user", cascade="all, delete-orphan")


class Selfie(Base):
    """A user photo uploaded to B2. Source for all API calls."""
    __tablename__ = "selfies"

    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False)
    b2_key            = Column(String(512), nullable=False)   # permanent storage key
    b2_url            = Column(String(2048), nullable=False)  # presigned URL (7 days)
    original_filename = Column(String(256), nullable=True)
    width             = Column(Integer, nullable=True)
    height            = Column(Integer, nullable=True)
    uploaded_at       = Column(DateTime, default=datetime.utcnow)

    user    = relationship("User", back_populates="selfies")
    results = relationship("Result", back_populates="selfie")


class Result(Base):
    """One row per YouCam API result. Result image re-uploaded to B2."""
    __tablename__ = "results"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    selfie_id   = Column(Integer, ForeignKey("selfies.id"), nullable=True)
    module      = Column(String(64), nullable=False)  # skin|palette|hair_color|hair_style|eye|clothes
    input_json  = Column(Text, nullable=True)         # JSON of params sent to API
    result_json = Column(Text, nullable=True)         # Full API response stored
    result_b2_key = Column(String(512), nullable=True)  # Result image permanent key
    result_url  = Column(String(2048), nullable=True)   # Presigned URL (7 days)
    created_at  = Column(DateTime, default=datetime.utcnow)

    user   = relationship("User", back_populates="results")
    selfie = relationship("Selfie", back_populates="results")


class Asset(Base):
    """Admin-uploaded catalog assets: lenses, garments, hairstyle references."""
    __tablename__ = "assets"

    id            = Column(Integer, primary_key=True, index=True)
    category      = Column(String(32), nullable=False)  # lens|garment|hairstyle
    name          = Column(String(128), nullable=False)
    b2_key        = Column(String(512), nullable=False)
    b2_url        = Column(String(2048), nullable=False)  # presigned URL
    thumbnail_url = Column(String(2048), nullable=True)
    meta_json     = Column(Text, nullable=True)           # extra params JSON
    created_at    = Column(DateTime, default=datetime.utcnow)


class CuratedLook(Base):
    """Admin-curated complete makeover bundles."""
    __tablename__ = "curated_looks"

    id                 = Column(Integer, primary_key=True, index=True)
    title              = Column(String(128), nullable=False)
    description        = Column(String(512), nullable=True)
    target_undertone   = Column(String(32), default="Any", nullable=False)  # Warm | Cool | Neutral | Any
    hair_color         = Column(String(32), default="#8c3a27", nullable=False)
    lens_asset_id      = Column(Integer, ForeignKey("assets.id"), nullable=True)
    garment_asset_id   = Column(Integer, ForeignKey("assets.id"), nullable=True)
    preview_url        = Column(String(2048), nullable=True)
    is_featured        = Column(Boolean, default=True)
    created_at         = Column(DateTime, default=datetime.utcnow)

    lens_asset    = relationship("Asset", foreign_keys=[lens_asset_id])
    garment_asset = relationship("Asset", foreign_keys=[garment_asset_id])


class BrandModel(Base):
    """Fashion models uploaded by brands or preloaded for casting fitting tests."""
    __tablename__ = "brand_models"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    name        = Column(String(128), nullable=False)
    gender      = Column(String(32), default="Female")
    undertone   = Column(String(32), default="Warm")  # Warm | Cool | Neutral | Olive
    height      = Column(String(32), nullable=True)   # e.g. "5'10 / 178cm"
    notes       = Column(Text, nullable=True)
    b2_key      = Column(String(512), nullable=True)
    b2_url      = Column(String(2048), nullable=False)
    is_preset   = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


class BrandProduct(Base):
    """Garment/item catalog uploaded by brands for virtual shoot fittings."""
    __tablename__ = "brand_products"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    title       = Column(String(128), nullable=False)
    sku         = Column(String(64), nullable=True)
    category    = Column(String(64), default="auto")  # auto | top | dress | outerwear | pants | skirt
    color       = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    b2_key      = Column(String(512), nullable=True)
    b2_url      = Column(String(2048), nullable=False)
    is_preset   = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


class BrandBatch(Base):
    """A batch session running multi-product x multi-model fitting combinations."""
    __tablename__ = "brand_batches"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    title           = Column(String(256), nullable=False)
    mode            = Column(String(32), nullable=False)  # item_to_models | model_to_items | matrix
    total_pairs     = Column(Integer, default=0)
    completed_pairs = Column(Integer, default=0)
    status          = Column(String(32), default="pending")  # pending | processing | completed | failed
    created_at      = Column(DateTime, default=datetime.utcnow)

    pair_results = relationship("BrandPairResult", back_populates="batch", cascade="all, delete-orphan", order_by="BrandPairResult.id")


class BrandPairResult(Base):
    """An individual garment + model pairing result generated via AI."""
    __tablename__ = "brand_pair_results"

    id             = Column(Integer, primary_key=True, index=True)
    batch_id       = Column(Integer, ForeignKey("brand_batches.id"), nullable=False)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id     = Column(Integer, ForeignKey("brand_products.id"), nullable=False)
    model_id       = Column(Integer, ForeignKey("brand_models.id"), nullable=False)
    youcam_task_id = Column(String(256), nullable=True)
    status         = Column(String(32), default="queued")  # queued | processing | success | error
    result_b2_key  = Column(String(512), nullable=True)
    result_url     = Column(String(2048), nullable=True)
    error_message  = Column(Text, nullable=True)
    casting_status = Column(String(32), default="undecided")  # undecided | shortlisted | booked | passed
    notes          = Column(Text, nullable=True)
    fit_score      = Column(Integer, nullable=True)  # 1-100 score or match rating
    created_at     = Column(DateTime, default=datetime.utcnow)

    batch   = relationship("BrandBatch", back_populates="pair_results")
    product = relationship("BrandProduct", foreign_keys=[product_id])
    model   = relationship("BrandModel", foreign_keys=[model_id])


# ─── Data Access Helpers ───────────────────────────────────────────────────────

def get_latest_selfie(db, user_id: int):
    """Fetch the latest uploaded selfie for a user."""
    if not user_id:
        return None
    return db.query(Selfie).filter(Selfie.user_id == user_id).order_by(Selfie.id.desc()).first()


def get_user_skin_summary(db, user_id: int):
    """
    Fetch the latest skin analysis / color palette result for a user.
    Returns parsed dictionary of skin metrics and undertone if available.
    """
    if not user_id:
        return None
    
    import json
    # Check palette result first for undertone
    palette_res = db.query(Result).filter(
        Result.user_id == user_id,
        Result.module == "palette",
        Result.result_json.isnot(None)
    ).order_by(Result.id.desc()).first()

    skin_res = db.query(Result).filter(
        Result.user_id == user_id,
        Result.module == "skin",
        Result.result_json.isnot(None)
    ).order_by(Result.id.desc()).first()

    summary = {
        "undertone": None,
        "skin_type": None,
        "skin_age": None,
        "overall_score": None,
        "palette_result_id": palette_res.id if palette_res else None,
        "skin_result_id": skin_res.id if skin_res else None,
    }

    if palette_res and palette_res.result_json:
        try:
            pj = json.loads(palette_res.result_json)
            data_results = pj.get("data", {}).get("results", {})
            from utils import parse_palette_data
            parsed = parse_palette_data(data_results)
            if parsed.get("undertone"):
                summary["undertone"] = parsed.get("undertone")
        except Exception:
            pass

    if skin_res and skin_res.result_json:
        try:
            sj = json.loads(skin_res.result_json)
            outputs = sj.get("data", {}).get("results", {}).get("output", [])
            for item in outputs:
                k = item.get("action")
                if k == "skin_type":
                    summary["skin_type"] = item.get("result", {}).get("skin_type")
                elif k == "age_spot":
                    summary["skin_age"] = item.get("result", {}).get("skin_age")
        except Exception:
            pass

    return summary if (summary["undertone"] or summary["skin_type"] or summary["skin_result_id"]) else None


# ─── Session Dependency ────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

