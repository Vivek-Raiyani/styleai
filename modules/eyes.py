"""
Eye Lens module — Virtual Contact Lens Try-On.
Uses eye-color-vto endpoint with intensity, enlargement, and smoothing controls.
"""
import json
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

import logging
from db import get_db, Selfie, Result, Asset, get_latest_selfie
from auth import get_current_user, create_guest_user
from utils import render, render_partial
from storage import upload_fastapi_file, upload_base64_image, download_and_upload
from youcam_client import EYE_LENS, start_task, check_task, eye_lens_payload

router = APIRouter(tags=["eyes"])
logger = logging.getLogger("styleai.eyes")


@router.get("/", response_class=HTMLResponse)
async def eyes_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    user_id = current_user.id if current_user else None
    latest_selfie = get_latest_selfie(db, user_id)
    lens_assets = db.query(Asset).filter(Asset.category == "lens").all()
    return render(
        request, "eyes/index.html", db,
        active_nav="eyes",
        latest_selfie=latest_selfie,
        lens_assets=lens_assets
    )


@router.post("/start", response_class=HTMLResponse)
async def eyes_start(
    request:         Request,
    db:              Session               = Depends(get_db),
    selfie_file:     Optional[UploadFile]  = File(None),
    base64_image:    Optional[str]         = Form(None),
    lens_asset_url:  Optional[str]         = Form(None),
    custom_lens_file: Optional[UploadFile] = File(None),
    intensity:       int                   = Form(70),
    enlargement:     int                   = Form(0),
    smooth_strength: int                   = Form(50),
    smooth_color:    int                   = Form(50),
):
    current_user = get_current_user(request, db)
    if not current_user:
        current_user = create_guest_user(db)
        request.session["user_id"] = current_user.id

    latest_selfie = get_latest_selfie(db, current_user.id)
    src_url = None
    selfie_id = None

    try:
        if selfie_file and selfie_file.filename:
            b2_src = await upload_fastapi_file(selfie_file)
            selfie = Selfie(user_id=current_user.id, b2_key=b2_src["key"], b2_url=b2_src["url"])
            db.add(selfie)
            db.commit()
            db.refresh(selfie)
            src_url = b2_src["url"]
            selfie_id = selfie.id
        elif base64_image and len(base64_image) > 50:
            b2_src = upload_base64_image(base64_image)
            selfie = Selfie(user_id=current_user.id, b2_key=b2_src["key"], b2_url=b2_src["url"])
            db.add(selfie)
            db.commit()
            db.refresh(selfie)
            src_url = b2_src["url"]
            selfie_id = selfie.id
        elif latest_selfie:
            src_url = latest_selfie.b2_url
            selfie_id = latest_selfie.id
        else:
            return HTMLResponse('<p class="text-error">No selfie image provided. Please select or upload a photo.</p>', status_code=400)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Photo upload failed: {e}</p>', status_code=500)

    # 2. Get lens pattern URL
    lens_url = lens_asset_url
    if custom_lens_file and custom_lens_file.filename:
        b2_lens = await upload_fastapi_file(custom_lens_file)
        lens_url = b2_lens["url"]

    if not lens_url:
        return HTMLResponse('<p class="text-error">Please choose a lens pattern or upload one.</p>', status_code=400)

    # 3. Payload
    payload = eye_lens_payload(
        src_url=src_url,
        lens_url=lens_url,
        intensity=intensity,
        enlargement=enlargement,
        smooth_strength=smooth_strength,
        smooth_color=smooth_color,
    )

    try:
        task_id = await start_task(EYE_LENS, payload)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">YouCam API error: {e}</p>', status_code=500)

    result = Result(
        user_id=current_user.id,
        selfie_id=selfie_id,
        module="eyes",
        input_json=json.dumps(payload),
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return render_partial(
        request, "eyes/partials/polling.html",
        task_id=task_id,
        result_id=result.id
    )


@router.get("/status/{task_id}", response_class=HTMLResponse)
async def eyes_status(
    task_id:   str,
    request:   Request,
    db:        Session = Depends(get_db),
    result_id: int     = 0,
):
    try:
        payload = await check_task(EYE_LENS, task_id)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Polling error: {e}</p>', status_code=500)

    status = payload.get("data", {}).get("task_status")

    if status not in ("success", "error"):
        return render_partial(
            request, "eyes/partials/polling.html",
            task_id=task_id,
            result_id=result_id
        )

    if status == "error":
        err = payload.get("data", {}).get("error", "Unknown error")
        return HTMLResponse(
            f'<div class="card" style="border-color:var(--status-error-fg)">'
            f'<p class="text-error">Eye lens try-on failed: {err}</p></div>'
        )

    # Success: fetch image output URL
    results_obj = payload.get("data", {}).get("results", {})
    output_url = results_obj.get("url") or results_obj.get("dst_file_url") or results_obj.get("output_url") or results_obj.get("image_url")

    permanent_url = output_url
    if output_url:
        try:
            persisted = await download_and_upload(output_url, prefix="styleai/eyes")
            permanent_url = persisted["url"]
        except Exception:
            permanent_url = output_url

    result_obj = db.query(Result).filter(Result.id == result_id).first()
    if result_obj:
        result_obj.result_json = json.dumps(payload)
        result_obj.result_url = permanent_url
        db.commit()

    return render_partial(
        request, "eyes/partials/result.html",
        output_url=permanent_url
    )
