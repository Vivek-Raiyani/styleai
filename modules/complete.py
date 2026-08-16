"""
Complete Look Wizard module.
Chains: Selfie Upload -> Skin Analysis (optional if cached) -> Hair Transformation -> Eye Lens VTO (optional) -> Clothes VTO (optional) -> Before/After Reveal.
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from db import get_db, Selfie, Result, Asset, CuratedLook, get_latest_selfie, get_user_skin_summary
from auth import get_current_user, create_guest_user
from utils import render, render_partial, format_api_error
from storage import upload_fastapi_file, upload_base64_image, download_and_upload
from youcam_client import (
    SKIN_ANALYSIS, HAIR_COLOR, HAIR_TRANSFER, EYE_LENS, CLOTH_VTO,
    start_task, check_task,
    skin_analysis_payload, hair_color_payload, hair_transfer_payload, eye_lens_payload, cloth_vto_payload
)

router = APIRouter(tags=["complete"])
logger = logging.getLogger("styleai.complete")


@router.get("/", response_class=HTMLResponse)
async def complete_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    user_id = current_user.id if current_user else None

    latest_selfie = get_latest_selfie(db, user_id)
    skin_summary  = get_user_skin_summary(db, user_id)
    curated_looks = db.query(CuratedLook).all()
    lenses        = db.query(Asset).filter(Asset.category == "lens").limit(12).all()
    garments      = db.query(Asset).filter(Asset.category == "garment").limit(12).all()
    hairstyles    = db.query(Asset).filter(Asset.category == "hairstyle").all()

    return render(
        request, "complete/index.html", db,
        active_nav="complete",
        latest_selfie=latest_selfie,
        skin_summary=skin_summary,
        curated_looks=curated_looks,
        lenses=lenses,
        garments=garments,
        hairstyles=hairstyles,
    )


@router.post("/start", response_class=HTMLResponse)
async def complete_start(
    request:            Request,
    db:                 Session               = Depends(get_db),
    selfie_file:        Optional[UploadFile]  = File(None),
    base64_image:       Optional[str]         = Form(None),
    body_file:          Optional[UploadFile]  = File(None),
    base64_body_image:  Optional[str]         = Form(None),
    body_preset_url:    Optional[str]         = Form(None),
    hair_mode:          str                   = Form("color"),
    hair_color_choice:  str                   = Form("#8c3a27"),
    hairstyle_ref_url:  Optional[str]         = Form(None),
    lens_choice_url:    Optional[str]         = Form(None),
    garment_choice_url: Optional[str]         = Form(None),
):
    current_user = get_current_user(request, db)
    if not current_user:
        current_user = create_guest_user(db)
        request.session["user_id"] = current_user.id

    latest_selfie = get_latest_selfie(db, current_user.id)
    skin_summary  = get_user_skin_summary(db, current_user.id)

    selfie_url = None
    selfie_id = None
    is_new_upload = False

    # 1. Determine Face Portrait Source
    if selfie_file and selfie_file.filename:
        try:
            b2 = await upload_fastapi_file(selfie_file)
            selfie = Selfie(user_id=current_user.id, b2_key=b2["key"], b2_url=b2["url"])
            db.add(selfie)
            db.commit()
            db.refresh(selfie)
            selfie_url = b2["url"]
            selfie_id = selfie.id
            is_new_upload = True
        except Exception as e:
            return HTMLResponse(f'<p class="text-error">Face photo upload failed: {e}</p>', status_code=500)
    elif base64_image and len(base64_image) > 50:
        try:
            b2 = upload_base64_image(base64_image)
            selfie = Selfie(user_id=current_user.id, b2_key=b2["key"], b2_url=b2["url"])
            db.add(selfie)
            db.commit()
            db.refresh(selfie)
            selfie_url = b2["url"]
            selfie_id = selfie.id
            is_new_upload = True
        except Exception as e:
            return HTMLResponse(f'<p class="text-error">Camera selfie upload failed: {e}</p>', status_code=500)
    elif latest_selfie:
        selfie_url = latest_selfie.b2_url
        selfie_id = latest_selfie.id
    else:
        return HTMLResponse('<p class="text-error">Please upload a face selfie photo first for facial styling.</p>', status_code=400)

    # 2. Determine Body / Torso Source (For Virtual Try-On)
    body_url = None
    if body_file and body_file.filename:
        try:
            b2_body = await upload_fastapi_file(body_file)
            body_url = b2_body["url"]
        except Exception as e:
            logger.warning(f"Body photo upload error: {e}")
    elif base64_body_image and len(base64_body_image) > 50:
        try:
            b2_body = upload_base64_image(base64_body_image)
            body_url = b2_body["url"]
        except Exception as e:
            logger.warning(f"Body camera upload error: {e}")
    elif body_preset_url and len(body_preset_url) > 10:
        body_url = body_preset_url
    elif garment_choice_url:
        # Default studio silhouette if user wants clothing try-on but didn't upload full body
        body_url = "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=800&q=80"

    # 3. Optimization: If skin diagnosis already cached, jump to Step 2
    if not is_new_upload and skin_summary and skin_summary.get("undertone"):
        logger.info(f"Using cached skin diagnosis for user {current_user.id}. Launching Hair Step 2.")
        try:
            if hair_mode == "transfer" and hairstyle_ref_url:
                hair_payload = hair_transfer_payload(src_url=selfie_url, ref_url=hairstyle_ref_url)
                step2_task_id = await start_task(HAIR_TRANSFER, hair_payload)
            else:
                hair_payload = hair_color_payload(src_url=selfie_url, color=hair_color_choice)
                step2_task_id = await start_task(HAIR_COLOR, hair_payload)
        except Exception as e:
            return HTMLResponse(f'<p class="text-error">Hair Transformation API Error: {e}</p>', status_code=500)

        result = Result(
            user_id=current_user.id,
            selfie_id=selfie_id,
            module="complete",
            input_json=json.dumps({
                "selfie_url": selfie_url,
                "body_url": body_url,
                "hair_mode": hair_mode,
                "hair_color": hair_color_choice,
                "hairstyle_ref_url": hairstyle_ref_url,
                "lens_url": lens_choice_url,
                "garment_url": garment_choice_url,
                "cached_undertone": skin_summary.get("undertone"),
            }),
        )
        db.add(result)
        db.commit()
        db.refresh(result)

        return render_partial(
            request, "complete/partials/step2_polling.html",
            task_id=step2_task_id,
            result_id=result.id,
            selfie_url=selfie_url,
            body_url=body_url,
            hair_mode=hair_mode,
            hair_color=hair_color_choice,
            hairstyle_ref_url=hairstyle_ref_url,
            lens_url=lens_choice_url,
            garment_url=garment_choice_url,
        )

    # 4. Otherwise, Start Step 1: Skin analysis baseline
    try:
        task_id = await start_task(SKIN_ANALYSIS, skin_analysis_payload(selfie_url))
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Skin Analysis API Error: {e}</p>', status_code=500)

    result = Result(
        user_id=current_user.id,
        selfie_id=selfie_id,
        module="complete",
        input_json=json.dumps({
            "selfie_url": selfie_url,
            "body_url": body_url,
            "hair_mode": hair_mode,
            "hair_color": hair_color_choice,
            "hairstyle_ref_url": hairstyle_ref_url,
            "lens_url": lens_choice_url,
            "garment_url": garment_choice_url,
        }),
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return render_partial(
        request, "complete/partials/step1_polling.html",
        task_id=task_id,
        result_id=result.id,
        selfie_url=selfie_url,
        body_url=body_url,
        hair_mode=hair_mode,
        hair_color=hair_color_choice,
        hairstyle_ref_url=hairstyle_ref_url,
        lens_url=lens_choice_url,
        garment_url=garment_choice_url,
    )


# ─── Step 1: Skin Analysis Polling ─────────────────────────────────────────────

@router.get("/step1/status/{task_id}", response_class=HTMLResponse)
async def step1_status(
    task_id:            str,
    result_id:         int,
    selfie_url:        str,
    body_url:          Optional[str] = None,
    hair_mode:         str           = "color",
    hair_color:        str           = "#8c3a27",
    hairstyle_ref_url: Optional[str] = None,
    lens_url:          Optional[str] = None,
    garment_url:       Optional[str] = None,
    request:           Request       = None,
    db:                Session       = Depends(get_db),
):
    try:
        payload = await check_task(SKIN_ANALYSIS, task_id)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Polling error: {e}</p>', status_code=500)

    status = payload.get("data", {}).get("task_status")

    if status not in ("success", "error"):
        return render_partial(
            request, "complete/partials/step1_polling.html",
            task_id=task_id,
            result_id=result_id,
            selfie_url=selfie_url,
            body_url=body_url,
            hair_mode=hair_mode,
            hair_color=hair_color,
            hairstyle_ref_url=hairstyle_ref_url,
            lens_url=lens_url,
            garment_url=garment_url,
        )

    if status == "error":
        return HTMLResponse('<p class="text-error">Step 1 (Skin Analysis) failed. Please check the photo.</p>')

    # Step 1 Success -> Launch Step 2 (Hair Transformation on Selfie)
    try:
        if hair_mode == "transfer" and hairstyle_ref_url:
            hair_payload = hair_transfer_payload(src_url=selfie_url, ref_url=hairstyle_ref_url)
            step2_task_id = await start_task(HAIR_TRANSFER, hair_payload)
        else:
            hair_payload = hair_color_payload(src_url=selfie_url, color=hair_color)
            step2_task_id = await start_task(HAIR_COLOR, hair_payload)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Hair Transformation start error: {e}</p>', status_code=500)

    return render_partial(
        request, "complete/partials/step2_polling.html",
        task_id=step2_task_id,
        result_id=result_id,
        selfie_url=selfie_url,
        body_url=body_url,
        hair_mode=hair_mode,
        hair_color=hair_color,
        hairstyle_ref_url=hairstyle_ref_url,
        lens_url=lens_url,
        garment_url=garment_url,
    )


# ─── Step 2: Hair Transformation Polling ──────────────────────────────────────

@router.get("/step2/status/{task_id}", response_class=HTMLResponse)
async def step2_status(
    task_id:            str,
    result_id:         int,
    selfie_url:        str,
    body_url:          Optional[str] = None,
    hair_mode:         str           = "color",
    hair_color:        str           = "#8c3a27",
    hairstyle_ref_url: Optional[str] = None,
    lens_url:          Optional[str] = None,
    garment_url:       Optional[str] = None,
    request:           Request       = None,
    db:                Session       = Depends(get_db),
):
    endpoint = HAIR_TRANSFER if hair_mode == "transfer" else HAIR_COLOR
    try:
        payload = await check_task(endpoint, task_id)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Polling error: {e}</p>', status_code=500)

    status = payload.get("data", {}).get("task_status")

    if status not in ("success", "error"):
        return render_partial(
            request, "complete/partials/step2_polling.html",
            task_id=task_id,
            result_id=result_id,
            selfie_url=selfie_url,
            body_url=body_url,
            hair_mode=hair_mode,
            hair_color=hair_color,
            hairstyle_ref_url=hairstyle_ref_url,
            lens_url=lens_url,
            garment_url=garment_url,
        )

    if status == "error":
        return HTMLResponse('<p class="text-error">Step 2 (Hair Transformation) failed.</p>')

    results_obj = payload.get("data", {}).get("results", {})
    hair_output_url = results_obj.get("url") or results_obj.get("dst_file_url") or results_obj.get("output_url")

    # Persist intermediate hair output
    final_hair_url = hair_output_url or selfie_url
    if hair_output_url:
        try:
            persisted = await download_and_upload(hair_output_url, prefix="styleai/complete")
            final_hair_url = persisted["url"]
        except Exception:
            pass

    # Chain into Step 3 (Eye Lens on Face) if lens selected
    if lens_url:
        try:
            lens_payload = eye_lens_payload(src_url=final_hair_url, lens_url=lens_url)
            step3_task_id = await start_task(EYE_LENS, lens_payload)
            return render_partial(
                request, "complete/partials/step3_polling.html",
                task_id=step3_task_id,
                result_id=result_id,
                selfie_url=selfie_url,
                body_url=body_url,
                hair_output_url=final_hair_url,
                garment_url=garment_url,
                hair_color=hair_color,
            )
        except Exception as e:
            logger.warning(f"Lens chain failed, falling back: {e}")

    # Chain into Step 4 (Clothes VTO on Body) if garment selected and body_url provided
    if garment_url and body_url:
        try:
            cloth_payload = cloth_vto_payload(src_url=body_url, ref_url=garment_url)
            step4_task_id = await start_task(CLOTH_VTO, cloth_payload)
            return render_partial(
                request, "complete/partials/step4_polling.html",
                task_id=step4_task_id,
                result_id=result_id,
                selfie_url=selfie_url,
                body_url=body_url,
                facial_makeover_url=final_hair_url,
                hair_color=hair_color,
            )
        except Exception as e:
            logger.warning(f"Garment chain failed: {e}")

    # Otherwise: Complete reveal
    result_obj = db.query(Result).filter(Result.id == result_id).first()
    if result_obj:
        result_obj.result_url = final_hair_url
        db.commit()

    return render_partial(
        request, "complete/partials/final_reveal.html",
        original_url=selfie_url,
        facial_makeover_url=final_hair_url,
        body_url=body_url,
        outfit_makeover_url=None,
        hair_color=hair_color,
    )


# ─── Step 3: Eye Lens Polling ──────────────────────────────────────────────────

@router.get("/step3/status/{task_id}", response_class=HTMLResponse)
async def step3_status(
    task_id:             str,
    result_id:           int,
    selfie_url:          str,
    hair_output_url:     str,
    body_url:            Optional[str] = None,
    garment_url:         Optional[str] = None,
    hair_color:          str           = "#8c3a27",
    request:             Request       = None,
    db:                  Session       = Depends(get_db),
):
    try:
        payload = await check_task(EYE_LENS, task_id)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Polling error: {e}</p>', status_code=500)

    status = payload.get("data", {}).get("task_status")

    if status not in ("success", "error"):
        return render_partial(
            request, "complete/partials/step3_polling.html",
            task_id=task_id,
            result_id=result_id,
            selfie_url=selfie_url,
            body_url=body_url,
            hair_output_url=hair_output_url,
            garment_url=garment_url,
            hair_color=hair_color,
        )

    results_obj = payload.get("data", {}).get("results", {})
    lens_output_url = results_obj.get("url") or results_obj.get("dst_file_url") or hair_output_url

    if lens_output_url:
        try:
            persisted = await download_and_upload(lens_output_url, prefix="styleai/complete")
            lens_output_url = persisted["url"]
        except Exception:
            pass

    # Chain into Step 4 (Clothes VTO on Body) if garment selected and body_url provided
    if garment_url and body_url:
        try:
            cloth_payload = cloth_vto_payload(src_url=body_url, ref_url=garment_url)
            step4_task_id = await start_task(CLOTH_VTO, cloth_payload)
            return render_partial(
                request, "complete/partials/step4_polling.html",
                task_id=step4_task_id,
                result_id=result_id,
                selfie_url=selfie_url,
                body_url=body_url,
                facial_makeover_url=lens_output_url,
                hair_color=hair_color,
            )
        except Exception as e:
            logger.warning(f"Garment chain failed: {e}")

    # Complete reveal
    result_obj = db.query(Result).filter(Result.id == result_id).first()
    if result_obj:
        result_obj.result_url = lens_output_url
        db.commit()

    return render_partial(
        request, "complete/partials/final_reveal.html",
        original_url=selfie_url,
        facial_makeover_url=lens_output_url,
        body_url=body_url,
        outfit_makeover_url=None,
        hair_color=hair_color,
    )


# ─── Step 4: Clothes VTO Polling ───────────────────────────────────────────────

@router.get("/step4/status/{task_id}", response_class=HTMLResponse)
async def step4_status(
    task_id:             str,
    result_id:           int,
    selfie_url:          str,
    body_url:            str,
    facial_makeover_url: str,
    hair_color:          str     = "#8c3a27",
    request:             Request = None,
    db:                  Session = Depends(get_db),
):
    try:
        payload = await check_task(CLOTH_VTO, task_id)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Polling error: {e}</p>', status_code=500)

    status = payload.get("data", {}).get("task_status")

    if status not in ("success", "error"):
        return render_partial(
            request, "complete/partials/step4_polling.html",
            task_id=task_id,
            result_id=result_id,
            selfie_url=selfie_url,
            body_url=body_url,
            facial_makeover_url=facial_makeover_url,
            hair_color=hair_color,
        )

    results_obj = payload.get("data", {}).get("results", {})
    final_clothing_url = results_obj.get("url") or results_obj.get("dst_file_url") or body_url

    if final_clothing_url:
        try:
            persisted = await download_and_upload(final_clothing_url, prefix="styleai/complete")
            final_clothing_url = persisted["url"]
        except Exception:
            pass

    # Save to Result
    result_obj = db.query(Result).filter(Result.id == result_id).first()
    if result_obj:
        result_obj.result_url = final_clothing_url
        result_obj.output_json = json.dumps({
            "facial_url": facial_makeover_url,
            "outfit_url": final_clothing_url,
        })
        db.commit()

    return render_partial(
        request, "complete/partials/final_reveal.html",
        original_url=selfie_url,
        facial_makeover_url=facial_makeover_url,
        body_url=body_url,
        outfit_makeover_url=final_clothing_url,
        hair_color=hair_color,
    )
