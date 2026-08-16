"""
Hair Studio module — Hair Color Simulation (Full & Ombre) & Hairstyle Transfer.
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
from youcam_client import (
    HAIR_COLOR, HAIR_TRANSFER,
    start_task, check_task,
    hair_color_payload, hair_transfer_payload
)

router = APIRouter(tags=["hair"])
logger = logging.getLogger("styleai.hair")


@router.get("/", response_class=HTMLResponse)
async def hair_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    user_id = current_user.id if current_user else None
    latest_selfie = get_latest_selfie(db, user_id)
    hairstyle_assets = db.query(Asset).filter(Asset.category == "hairstyle").all()
    return render(
        request, "hair/index.html", db,
        active_nav="hair",
        latest_selfie=latest_selfie,
        hairstyle_assets=hairstyle_assets
    )


@router.post("/color/start", response_class=HTMLResponse)
async def hair_color_start(
    request:         Request,
    db:              Session               = Depends(get_db),
    selfie_file:     Optional[UploadFile]  = File(None),
    base64_image:    Optional[str]         = Form(None),
    color:           str                   = Form("#8c3a27"),
    pattern:         str                   = Form("full"),
    second_color:    Optional[str]         = Form(None),
    color_intensity: int                   = Form(70),
    shine_intensity: int                   = Form(50),
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
            return HTMLResponse('<p class="text-error">No photo provided. Please upload or take a selfie.</p>', status_code=400)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Upload failed: {e}</p>', status_code=500)

    # Format payload
    payload = hair_color_payload(
        src_url=src_url,
        color=color,
        pattern=pattern,
        second_color=second_color,
        color_intensity=color_intensity,
        shine_intensity=shine_intensity,
    )

    try:
        task_id = await start_task(HAIR_COLOR, payload)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">YouCam API error: {e}</p>', status_code=500)

    result = Result(
        user_id=current_user.id,
        selfie_id=selfie_id,
        module="hair_color",
        input_json=json.dumps(payload),
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return render_partial(
        request, "hair/partials/polling.html",
        task_id=task_id,
        result_id=result.id,
        mode="color"
    )


@router.post("/transfer/start", response_class=HTMLResponse)
async def hair_transfer_start(
    request:         Request,
    db:              Session               = Depends(get_db),
    selfie_file:     Optional[UploadFile]  = File(None),
    base64_image:    Optional[str]         = Form(None),
    ref_asset_url:   Optional[str]         = Form(None),
    ref_file:        Optional[UploadFile]  = File(None),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return HTMLResponse('<p class="text-error">Please sign in first.</p>', status_code=401)

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
            return HTMLResponse('<p class="text-error">No source image provided. Please select or upload a photo.</p>', status_code=400)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Source upload failed: {e}</p>', status_code=500)

    # Check if multiple reference styles were submitted
    form_data = await request.form()
    multi_refs = form_data.getlist("ref_asset_urls")
    if len(multi_refs) > 1:
        return await hair_transfer_batch(request, db, selfie_file, base64_image)

    # Reference hairstyle image
    ref_url = ref_asset_url or (multi_refs[0] if multi_refs else None)
    if ref_file and ref_file.filename:
        b2_ref = await upload_fastapi_file(ref_file)
        ref_url = b2_ref["url"]

    if not ref_url:
        return HTMLResponse('<p class="text-error">Please select or upload a reference hairstyle.</p>', status_code=400)

    payload = hair_transfer_payload(src_url=src_url, ref_url=ref_url)

    try:
        task_id = await start_task(HAIR_TRANSFER, payload)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">YouCam API error: {e}</p>', status_code=500)

    result = Result(
        user_id=current_user.id,
        selfie_id=selfie_id,
        module="hair_transfer",
        input_json=json.dumps(payload),
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return render_partial(
        request, "hair/partials/polling.html",
        task_id=task_id,
        result_id=result.id,
        mode="transfer"
    )


@router.get("/status/{task_id}", response_class=HTMLResponse)
async def hair_status(
    task_id:   str,
    request:   Request,
    db:        Session = Depends(get_db),
    result_id: int     = 0,
    mode:      str     = "color"
):
    endpoint = HAIR_COLOR if mode == "color" else HAIR_TRANSFER
    try:
        payload = await check_task(endpoint, task_id)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Polling error: {e}</p>', status_code=500)

    status = payload.get("data", {}).get("task_status")

    if status not in ("success", "error"):
        return render_partial(
            request, "hair/partials/polling.html",
            task_id=task_id,
            result_id=result_id,
            mode=mode
        )

    if status == "error":
        err = payload.get("data", {}).get("error", "Unknown error")
        return HTMLResponse(
            f'<div class="card" style="border-color:var(--status-error-fg)">'
            f'<p class="text-error">Hair processing failed: {err}</p></div>'
        )

    # Success: fetch image output URL and re-upload to B2 for permanence
    results_obj = payload.get("data", {}).get("results", {})
    output_url = results_obj.get("url") or results_obj.get("dst_file_url") or results_obj.get("output_url") or results_obj.get("image_url")
    
    permanent_url = output_url
    if output_url:
        try:
            persisted = await download_and_upload(output_url, prefix="styleai/hair")
            permanent_url = persisted["url"]
        except Exception:
            permanent_url = output_url

    result_obj = db.query(Result).filter(Result.id == result_id).first()
    if result_obj:
        result_obj.result_json = json.dumps(payload)
        result_obj.result_url = permanent_url
        db.commit()

    return render_partial(
        request, "hair/partials/result.html",
        output_url=permanent_url,
        mode=mode
    )


# ─── Batch Multi-Hairstyle Transfer & In-Place Recoloring ──────────────────────

@router.post("/transfer/batch", response_class=HTMLResponse)
async def hair_transfer_batch(
    request:         Request,
    db:              Session               = Depends(get_db),
    selfie_file:     Optional[UploadFile]  = File(None),
    base64_image:    Optional[str]         = Form(None),
):
    current_user = get_current_user(request, db)
    if not current_user:
        current_user = create_guest_user(db)
        request.session["user_id"] = current_user.id

    form_data = await request.form()
    # Collect all selected reference style URLs
    ref_urls = form_data.getlist("ref_asset_urls")
    if not ref_urls:
        single_ref = form_data.get("ref_asset_url")
        if single_ref:
            ref_urls = [single_ref]

    if not ref_urls:
        return HTMLResponse('<p class="text-error">Please select at least 1 reference hairstyle.</p>', status_code=400)

    # Limit batch size to max 6 concurrent styles
    ref_urls = list(dict.fromkeys(ref_urls))[:6]

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
            return HTMLResponse('<p class="text-error">No photo provided. Please upload a portrait.</p>', status_code=400)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Upload failed: {e}</p>', status_code=500)

    # Look up asset names
    assets_by_url = {
        a.b2_url: a.name for a in db.query(Asset).filter(Asset.b2_url.in_(ref_urls)).all()
    }

    # Launch tasks concurrently
    import asyncio
    import base64 as b64

    async def start_single_style(url: str, idx: int):
        payload = hair_transfer_payload(src_url=src_url, ref_url=url)
        name = assets_by_url.get(url, f"Style #{idx + 1}")
        try:
            tid = await start_task(HAIR_TRANSFER, payload)
            res = Result(
                user_id=current_user.id,
                selfie_id=selfie_id,
                module="hair_transfer",
                input_json=json.dumps(payload),
            )
            db.add(res)
            db.commit()
            db.refresh(res)
            return {
                "task_id": tid,
                "result_id": res.id,
                "ref_url": url,
                "style_name": name,
                "status": "running",
                "output_url": None,
            }
        except Exception as e:
            return {
                "task_id": None,
                "result_id": None,
                "ref_url": url,
                "style_name": name,
                "status": "error",
                "error": str(e),
                "output_url": None,
            }

    tasks = [start_single_style(u, i) for i, u in enumerate(ref_urls)]
    items = await asyncio.gather(*tasks)

    batch_json = json.dumps(items)
    batch_data_encoded = b64.urlsafe_b64encode(batch_json.encode()).decode()

    return render_partial(
        request, "hair/partials/batch_polling.html",
        items=items,
        batch_data_encoded=batch_data_encoded,
    )


@router.get("/batch/status", response_class=HTMLResponse)
async def hair_batch_status(
    request: Request,
    batch_data: str,
    db: Session = Depends(get_db),
):
    import asyncio
    import base64 as b64

    try:
        raw_json = b64.urlsafe_b64decode(batch_data.encode()).decode()
        items = json.loads(raw_json)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Invalid batch data: {e}</p>', status_code=400)

    # Poll running tasks concurrently
    all_done = True
    for item in items:
        if item.get("status") == "running" and item.get("task_id"):
            try:
                res = await check_task(HAIR_TRANSFER, item["task_id"])
                task_status = res.get("data", {}).get("task_status")
                if task_status == "success":
                    results_obj = res.get("data", {}).get("results", {})
                    out_url = results_obj.get("url") or results_obj.get("dst_file_url") or results_obj.get("output_url")
                    
                    # Persist image to B2
                    perm_url = out_url
                    if out_url:
                        try:
                            persisted = await download_and_upload(out_url, prefix="styleai/hair")
                            perm_url = persisted["url"]
                        except Exception:
                            perm_url = out_url

                    item["status"] = "success"
                    item["output_url"] = perm_url

                    # Update result in DB
                    if item.get("result_id"):
                        r_obj = db.query(Result).filter(Result.id == item["result_id"]).first()
                        if r_obj:
                            r_obj.result_json = json.dumps(res)
                            r_obj.result_url = perm_url
                            db.commit()

                elif task_status == "error":
                    item["status"] = "error"
                    item["error"] = res.get("data", {}).get("error", "Failed")
                else:
                    all_done = False
            except Exception:
                all_done = False

    if not all_done:
        batch_json = json.dumps(items)
        batch_data_encoded = b64.urlsafe_b64encode(batch_json.encode()).decode()
        return render_partial(
            request, "hair/partials/batch_polling.html",
            items=items,
            batch_data_encoded=batch_data_encoded,
        )

    # All finished: filter successful outputs for display
    successful_items = [i for i in items if i.get("status") == "success" and i.get("output_url")]
    if not successful_items:
        return HTMLResponse(
            '<div class="card" style="border-color:var(--status-error-fg); text-align:center; padding:var(--sp-6);">'
            '<p class="text-error font-bold mb-1">Hairstyle Simulation Failed</p>'
            '<p class="muted text-xs">Please check that the portrait has clear face and hair visibility.</p>'
            '<button type="button" class="btn btn-secondary btn-sm mt-3" onclick="switchHairMode(\'transfer\')">Try Again</button>'
            '</div>'
        )

    return render_partial(
        request, "hair/partials/batch_result.html",
        items=successful_items,
    )


@router.post("/recolor/instant")
async def hair_recolor_instant(
    request:           Request,
    source_image_url:  str                   = Form(...),
    color:             str                   = Form("#8c3a27"),
    pattern:           str                   = Form("full"),
    second_color:      Optional[str]         = Form(None),
    color_intensity:   int                   = Form(75),
    shine_intensity:   int                   = Form(50),
    db:                Session               = Depends(get_db),
):
    """One-click instant hair recoloring for any generated hairstyle image."""
    current_user = get_current_user(request, db)
    if not current_user:
        current_user = create_guest_user(db)
        request.session["user_id"] = current_user.id

    payload = hair_color_payload(
        src_url=source_image_url,
        color=color,
        pattern=pattern,
        second_color=second_color,
        color_intensity=color_intensity,
        shine_intensity=shine_intensity,
    )

    try:
        from youcam_client import run_task
        res = await run_task(HAIR_COLOR, payload, interval=1.5, max_tries=30)
        results_obj = res.get("data", {}).get("results", {})
        out_url = results_obj.get("url") or results_obj.get("dst_file_url") or results_obj.get("output_url")

        perm_url = out_url
        if out_url:
            try:
                persisted = await download_and_upload(out_url, prefix="styleai/hair")
                perm_url = persisted["url"]
            except Exception:
                perm_url = out_url

        # Save result to DB
        new_res = Result(
            user_id=current_user.id,
            module="hair_color",
            input_json=json.dumps(payload),
            result_json=json.dumps(res),
            result_url=perm_url,
        )
        db.add(new_res)
        db.commit()

        return {"status": "success", "url": perm_url}
    except Exception as e:
        logger.error(f"Instant recolor failed: {e}")
        return {"status": "error", "error": str(e)}
