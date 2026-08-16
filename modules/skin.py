"""
Skin Analysis module — full HTMX async flow.
POST /skin/start  → uploads selfie → starts YouCam task → returns polling partial
GET  /skin/status/{task_id} → polls YouCam → returns spinner or result partial
"""
import json
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

import logging
from db import get_db, Selfie, Result, get_latest_selfie
from auth import get_current_user, create_guest_user, set_flash
from utils import render, render_partial, format_api_error
from storage import upload_fastapi_file, upload_base64_image, download_and_upload
from youcam_client import SKIN_ANALYSIS, start_task, check_task, skin_analysis_payload

router = APIRouter(tags=["skin"])
logger = logging.getLogger("styleai.skin")

_ENDPOINT = SKIN_ANALYSIS   # "v2.1/task/skin-analysis"


# ─── Page ─────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def skin_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    user_id = current_user.id if current_user else None
    latest_selfie = get_latest_selfie(db, user_id)
    return render(request, "skin/index.html", db, active_nav="skin", latest_selfie=latest_selfie)


# ─── Start task (called by upload form via HTMX) ──────────────────────────────

@router.post("/start", response_class=HTMLResponse)
async def skin_start(
    request:      Request,
    db:           Session    = Depends(get_db),
    selfie_file:  Optional[UploadFile] = File(None),
    base64_image: Optional[str]        = Form(None),
):
    current_user = get_current_user(request, db)
    if not current_user:
        current_user = create_guest_user(db)
        request.session["user_id"] = current_user.id

    latest_selfie = get_latest_selfie(db, current_user.id)
    src_url = None
    selfie_id = None

    # ── Upload selfie to B2 ──
    try:
        if selfie_file and selfie_file.filename:
            b2 = await upload_fastapi_file(selfie_file)
            selfie = Selfie(user_id=current_user.id, b2_key=b2["key"], b2_url=b2["url"])
            db.add(selfie)
            db.commit()
            db.refresh(selfie)
            src_url = b2["url"]
            selfie_id = selfie.id
        elif base64_image and len(base64_image) > 50:
            b2 = upload_base64_image(base64_image)
            selfie = Selfie(user_id=current_user.id, b2_key=b2["key"], b2_url=b2["url"])
            db.add(selfie)
            db.commit()
            db.refresh(selfie)
            src_url = b2["url"]
            selfie_id = selfie.id
        elif latest_selfie:
            src_url = latest_selfie.b2_url
            selfie_id = latest_selfie.id
        else:
            return HTMLResponse('<p class="text-error">No photo provided. Please select or take a photo.</p>', status_code=400)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Upload failed: {e}</p>', status_code=500)

    # ── Start YouCam task ──
    try:
        payload = skin_analysis_payload(src_url)
        logger.info(f"Sending request to YouCam API: {_ENDPOINT}")
        task_id = await start_task(_ENDPOINT, payload)
        logger.info(f"YouCam task created: {task_id}")
    except Exception as e:
        logger.exception("YouCam API start error")
        return HTMLResponse(f'<p class="text-error">YouCam API error: {e}</p>', status_code=500)

    # ── Store pending result ──
    result = Result(
        user_id=current_user.id,
        selfie_id=selfie_id,
        module="skin",
        input_json=json.dumps({"selfie_url": src_url}),
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    # ── Return HTMX polling partial ──
    return render_partial(
        request, "skin/partials/polling.html",
        task_id=task_id,
        result_id=result.id,
        selfie_url=b2["url"],
    )


# ─── Poll status (HTMX polls this every 2s) ───────────────────────────────────

@router.get("/status/{task_id}", response_class=HTMLResponse)
async def skin_status(
    task_id:   str,
    request:   Request,
    db:        Session = Depends(get_db),
    result_id: int     = 0,
):
    try:
        payload = await check_task(_ENDPOINT, task_id)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Polling error: {e}</p>', status_code=500)

    status = payload.get("data", {}).get("task_status")

    # ── Still processing: re-render spinner with same task_id ──
    if status not in ("success", "error"):
        return render_partial(
            request, "skin/partials/polling.html",
            task_id=task_id,
            result_id=result_id,
            selfie_url="",
        )

    # ── Error ──
    if status == "error":
        err = payload.get("data", {}).get("error", "Unknown error")
        friendly_msg = format_api_error(err)
        return HTMLResponse(
            f'<div class="card" style="border-color:var(--status-error-fg)">'
            f'<p class="text-error">{friendly_msg}</p></div>'
        )

    # ── Success: parse + save result ──
    results_data = payload.get("data", {}).get("results", {}).get("output", [])

    # Save full result JSON to DB
    result_obj = db.query(Result).filter(Result.id == result_id).first()
    if result_obj:
        result_obj.result_json = json.dumps(payload)
        db.commit()

    # Parse metrics
    metrics   = []
    skin_type = None
    overall   = None
    skin_age  = None

    for item in results_data:
        t = item.get("type")
        if t == "all":
            overall = round(item.get("score", 0))
        elif t == "skin_age":
            skin_age = item.get("score")
        elif t == "skin_type" and item.get("region") == "whole":
            skin_type = item.get("skin_type")
        elif t not in ("resize_image",) and "ui_score" in item:
            metrics.append({
                "type":      t,
                "label":     t.replace("_", " ").title(),
                "ui_score":  item["ui_score"],
                "raw_score": round(item.get("raw_score", 0), 1),
            })

    # Sort metrics descending by score for display
    metrics.sort(key=lambda m: m["ui_score"], reverse=True)

    return render_partial(
        request, "skin/partials/result.html",
        metrics=metrics,
        skin_type=skin_type,
        overall=overall,
        skin_age=skin_age,
    )
