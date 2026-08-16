"""
History Module — view, filter, and inspect past AI analyses and makeover runs with full inputs and outputs.
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from db import get_db, Result, Selfie
from auth import get_current_user, set_flash
from utils import render, render_partial

router = APIRouter(prefix="/history", tags=["history"])
logger = logging.getLogger("styleai.history")

MODULE_LABELS = {
    "skin":          {"label": "Skin Health", "icon": "🧬", "pill": "pill-lime"},
    "palette":       {"label": "Color DNA",   "icon": "🎨", "pill": "pill-clay"},
    "hair_color":    {"label": "Hair Color",  "icon": "💇", "pill": "pill-terracotta"},
    "hair_transfer": {"label": "Hairstyle",   "icon": "✂️", "pill": "pill-terracotta"},
    "eyes":          {"label": "Eye Lens",    "icon": "👁️", "pill": "pill-clay"},
    "clothes":       {"label": "Style (VTO)", "icon": "👗", "pill": "pill-lime"},
    "complete":      {"label": "Complete Look","icon": "✨", "pill": "pill-lime"},
}


@router.get("/", response_class=HTMLResponse)
async def history_page(
    request: Request,
    module:  str     = "",
    db:      Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        from auth import create_guest_user
        current_user = create_guest_user(db)
        request.session["user_id"] = current_user.id

    query = db.query(Result).filter(Result.user_id == current_user.id)
    if module:
        query = query.filter(Result.module == module)
    
    results = query.order_by(Result.created_at.desc()).all()

    formatted_results = []
    for r in results:
        meta = {}
        if r.result_json:
            try:
                meta = json.loads(r.result_json)
            except Exception:
                pass

        label_info = MODULE_LABELS.get(r.module, {"label": r.module.title(), "icon": "✦", "pill": "pill-clay"})

        formatted_results.append({
            "id": r.id,
            "module": r.module,
            "label": label_info["label"],
            "icon": label_info["icon"],
            "pill": label_info["pill"],
            "selfie_url": r.selfie.b2_url if r.selfie else None,
            "result_url": r.result_url,
            "created_at": r.created_at,
            "meta": meta,
        })

    return render(
        request, "history/index.html", db,
        active_nav="history",
        results=formatted_results,
        module_filter=module,
        module_labels=MODULE_LABELS,
    )


@router.get("/detail/{result_id}", response_class=HTMLResponse)
async def history_detail(
    result_id: int,
    request:   Request,
    db:        Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        from auth import create_guest_user
        current_user = create_guest_user(db)
        request.session["user_id"] = current_user.id

    query = db.query(Result).filter(Result.id == result_id)
    if not current_user.is_admin:
        query = query.filter(Result.user_id == current_user.id)
    result = query.first()

    if not result:
        return HTMLResponse("<p class='text-error'>Run not found or access denied.</p>", status_code=404)

    label_info = MODULE_LABELS.get(result.module, {"label": result.module.title(), "icon": "✦", "pill": "pill-clay"})

    # Parse input data
    input_data = {}
    if result.input_json:
        try:
            input_data = json.loads(result.input_json)
        except Exception:
            pass

    selfie_url = result.selfie.b2_url if result.selfie else (input_data.get("src_file_url") or input_data.get("src_url"))
    ref_url = (
        input_data.get("ref_file_url")
        or input_data.get("ref_url")
        or input_data.get("ref_asset_url")
        or input_data.get("item_asset_url")
        or input_data.get("lens_asset_url")
        or input_data.get("garment_url")
    )

    # Clean input parameters for UI display (hide raw URLs and technical internals)
    hidden_keys = {
        "src_file_url", "ref_file_url", "src_url", "ref_url", "selfie_url",
        "item_asset_url", "ref_asset_url", "lens_asset_url", "preset_source_url",
        "selfie_b2_key", "b2_url", "thumbnail_url", "miniserver_args",
        "pf_camera_kit", "format", "version", "dst_actions", "palettes"
    }
    clean_params = {}
    for k, v in input_data.items():
        if k not in hidden_keys and v is not None and v != "":
            label = k.replace("_", " ").title()
            if isinstance(v, dict):
                if "name" in v:
                    clean_params[label] = v["name"].title()
                else:
                    for subk, subv in v.items():
                        clean_params[f"{subk.replace('_', ' ').title()}"] = subv
            elif isinstance(v, list):
                continue
            else:
                clean_params[label] = v

    # Extract palettes colors if available
    hair_colors_applied = []
    palettes = input_data.get("palettes", [])
    if isinstance(palettes, list):
        for p in palettes:
            if isinstance(p, dict) and "color" in p:
                hair_colors_applied.append(p["color"])

    # Parse result data
    result_data = {}
    if result.result_json:
        try:
            result_data = json.loads(result.result_json)
        except Exception:
            pass

    metrics = []
    overall_score = None
    skin_type = None
    skin_age = None
    skin_tone = {}
    hair_color = {}
    eye_color = {}
    lip_color = {}
    undertone = None
    recommendations = []

    # Module-specific result unpacking
    if result.module == "skin":
        outputs = result_data.get("data", {}).get("results", {}).get("output", [])
        for item in outputs:
            t = item.get("type")
            if t == "all":
                overall_score = round(item.get("score", 0))
            elif t == "skin_age":
                skin_age = item.get("score")
            elif t == "skin_type" and item.get("region") == "whole":
                skin_type = item.get("skin_type")
            elif t not in ("resize_image",) and "ui_score" in item:
                metrics.append({
                    "label": t.replace("_", " ").title(),
                    "ui_score": item["ui_score"],
                })
        metrics.sort(key=lambda m: m["ui_score"], reverse=True)

    elif result.module == "palette":
        data_results = result_data.get("data", {}).get("results", {})
        from utils import parse_palette_data
        parsed = parse_palette_data(data_results)
        skin_tone = parsed.get("skin_tone", {})
        hair_color = parsed.get("hair_color", {})
        eye_color = parsed.get("eye_color", {})
        lip_color = parsed.get("lip_color", {})
        undertone = parsed.get("undertone", "Neutral")
        if undertone == "Warm":
            recommendations = [
                {"name": "Terracotta", "hex": "#c56a3f"},
                {"name": "Golden Olive", "hex": "#8c7b33"},
                {"name": "Warm Amber", "hex": "#d49137"},
                {"name": "Rich Camel", "hex": "#b08556"},
                {"name": "Burnt Peach", "hex": "#d9825b"}
            ]
        elif undertone == "Cool":
            recommendations = [
                {"name": "Icy Blue", "hex": "#6ea8d9"},
                {"name": "Deep Plum", "hex": "#5e2b4f"},
                {"name": "Emerald Jewel", "hex": "#2e6f5e"},
                {"name": "Rosewood", "hex": "#aa5b71"},
                {"name": "Soft Lavender", "hex": "#9c8cb9"}
            ]
        else:
            recommendations = [
                {"name": "Dusty Rose", "hex": "#c27c88"},
                {"name": "Sage Mist", "hex": "#7f9680"},
                {"name": "Soft Teal", "hex": "#4e878c"},
                {"name": "Warm Taupe", "hex": "#8d7b68"},
                {"name": "Mocha", "hex": "#5c4033"}
            ]

    return render_partial(
        request, "history/partials/detail_modal.html",
        result=result,
        label_info=label_info,
        selfie_url=selfie_url,
        ref_url=ref_url,
        result_url=result.result_url,
        clean_params=clean_params,
        hair_colors_applied=hair_colors_applied,
        input_data=input_data,
        module=result.module,
        metrics=metrics,
        overall_score=overall_score,
        skin_type=skin_type,
        skin_age=skin_age,
        skin_tone=skin_tone,
        hair_color=hair_color,
        eye_color=eye_color,
        lip_color=lip_color,
        undertone=undertone,
        recommendations=recommendations,
    )


@router.post("/delete/{result_id}")
async def delete_history_item(
    result_id: int,
    request:   Request,
    db:        Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/history", status_code=303)

    result = db.query(Result).filter(
        Result.id == result_id,
        Result.user_id == current_user.id
    ).first()

    if result:
        db.delete(result)
        db.commit()
        set_flash(request, "Item removed from history.", "neutral")

    return RedirectResponse("/history", status_code=303)
