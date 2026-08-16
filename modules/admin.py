"""
Admin module — Asset Catalog, Look Planner, and System Run Inspector.
Protected: admin users only.
"""
import json
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from db import get_db, Asset, CuratedLook, Result, Selfie, User, BrandModel, BrandProduct
from auth import get_current_user, set_flash
from utils import render
from storage import upload_bytes_sync

router = APIRouter(tags=["admin"])

CATEGORIES = ["garment", "shoes", "bag", "necklace", "earring", "lens", "hairstyle"]
UNDERTONES = ["Any", "Warm", "Cool", "Neutral", "Deep"]


def _require_admin(request, db):
    user = get_current_user(request, db)
    if not user or not user.is_admin:
        return None
    return user


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def admin_home(
    request:  Request,
    tab:      str     = "catalog",
    category: str     = "",
    db:       Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if not user:
        set_flash(request, "Admin access required. Please sign in with an admin account.", "error")
        return RedirectResponse("/auth/login", status_code=303)

    # 1. Assets
    asset_query = db.query(Asset)
    if category and category in CATEGORIES:
        asset_query = asset_query.filter(Asset.category == category)
    assets = asset_query.order_by(Asset.created_at.desc()).all()

    # 2. Curated Looks
    curated_looks = db.query(CuratedLook).order_by(CuratedLook.created_at.desc()).all()

    # 3. System Run Inspector
    recent_runs = db.query(Result).order_by(Result.created_at.desc()).limit(40).all()

    lenses = db.query(Asset).filter(Asset.category == "lens").all()
    garments = db.query(Asset).filter(Asset.category == "garment").all()

    # 4. Brand Presets Stats
    total_models = db.query(BrandModel).filter(BrandModel.is_preset == True).count()
    total_products = db.query(BrandProduct).filter(BrandProduct.is_preset == True).count()

    # 5. Maintenance Stats
    total_guests = db.query(User).filter(User.is_guest == True).count()
    total_registered = db.query(User).filter(User.is_guest == False).count()
    total_selfies = db.query(Selfie).count()
    total_results = db.query(Result).count()

    return render(
        request, "admin/index.html", db,
        active_nav="admin",
        tab=tab,
        assets=assets,
        curated_looks=curated_looks,
        recent_runs=recent_runs,
        categories=CATEGORIES,
        undertones=UNDERTONES,
        active_category=category,
        lenses=lenses,
        garments=garments,
        total_preset_models=total_models,
        total_preset_products=total_products,
        total_guests=total_guests,
        total_registered=total_registered,
        total_selfies=total_selfies,
        total_results=total_results,
    )


# ─── Upload asset ─────────────────────────────────────────────────────────────

@router.post("/upload", response_class=HTMLResponse)
async def admin_upload(
    request:  Request,
    name:     str        = Form(...),
    category: str        = Form(...),
    file:     UploadFile = File(...),
    meta:     str        = Form("{}"),
    db:       Session    = Depends(get_db),
):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    if category not in CATEGORIES:
        set_flash(request, "Invalid category.", "error")
        return RedirectResponse("/admin?tab=catalog", status_code=303)

    data = await file.read()
    ct   = file.content_type or "image/png"
    b2   = upload_bytes_sync(data, ct, prefix=f"styleai/catalog/{category}")

    asset = Asset(
        category=category,
        name=name,
        b2_key=b2["key"],
        b2_url=b2["url"],
        meta_json=meta,
    )
    db.add(asset)
    db.commit()

    set_flash(request, f'Asset "{name}" uploaded to {category} catalog.', "success")
    return RedirectResponse(f"/admin?tab=catalog&category={category}", status_code=303)


# ─── Delete asset ─────────────────────────────────────────────────────────────

@router.post("/delete/{asset_id}")
async def admin_delete(
    asset_id: int,
    request:  Request,
    db:       Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset:
        db.delete(asset)
        db.commit()
        set_flash(request, "Asset deleted.", "neutral")

    return RedirectResponse("/admin?tab=catalog", status_code=303)


# ─── Look Planner: Create Curated Look ────────────────────────────────────────

@router.post("/looks/create")
async def create_curated_look(
    request:          Request,
    title:            str           = Form(...),
    description:      str           = Form(""),
    target_undertone: str           = Form("Any"),
    hair_color:       str           = Form("#8c3a27"),
    lens_asset_id:    Optional[str] = Form(None),
    garment_asset_id: Optional[str] = Form(None),
    db:               Session       = Depends(get_db),
):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    lens_id = int(lens_asset_id) if lens_asset_id and lens_asset_id.isdigit() else None
    garment_id = int(garment_asset_id) if garment_asset_id and garment_asset_id.isdigit() else None

    look = CuratedLook(
        title=title,
        description=description,
        target_undertone=target_undertone,
        hair_color=hair_color,
        lens_asset_id=lens_id,
        garment_asset_id=garment_id,
    )
    db.add(look)
    db.commit()

    set_flash(request, f'Curated look "{title}" published!', "success")
    return RedirectResponse("/admin?tab=looks", status_code=303)


# ─── Look Planner: Delete Look ────────────────────────────────────────────────

@router.post("/looks/delete/{look_id}")
async def delete_curated_look(
    look_id: int,
    request: Request,
    db:      Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    look = db.query(CuratedLook).filter(CuratedLook.id == look_id).first()
    if look:
        db.delete(look)
        db.commit()
        set_flash(request, f'Look "{look.title}" removed.', "neutral")

    return RedirectResponse("/admin?tab=looks", status_code=303)


# ─── System Maintenance: Clear Guest & Testing Data ──────────────────────────

@router.post("/maintenance/clean-guests")
async def clean_guests_endpoint(
    request: Request,
    db:      Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    from clean_data import clean_guest_data
    stats = clean_guest_data(db)
    set_flash(
        request,
        f"Guest cleanup complete: {stats.get('guests_deleted', 0)} guest accounts, "
        f"{stats.get('selfies_deleted', 0)} selfies, and {stats.get('results_deleted', 0)} results removed.",
        "success",
    )
    return RedirectResponse("/admin?tab=maintenance", status_code=303)


@router.post("/maintenance/clean-test-data")
async def clean_test_data_endpoint(
    request: Request,
    db:      Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    from clean_data import clean_all_testing_data
    stats = clean_all_testing_data(db)
    set_flash(
        request,
        f"Complete test data purge finished: {stats.get('guests_deleted', 0)} guests removed, "
        f"{stats.get('total_selfies_purged', 0)} selfies purged, {stats.get('total_results_purged', 0)} results purged, "
        f"{stats.get('total_batches_purged', 0)} batch runs purged.",
        "success",
    )
    return RedirectResponse("/admin?tab=maintenance", status_code=303)
