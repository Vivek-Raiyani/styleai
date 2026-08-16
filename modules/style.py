"""
Virtual Try-On Suite module.
Supports 5 Generative VTO Categories:
1. Clothes (cloth-v4)
2. Shoes (v2.0/task/shoes)
3. Luxury Bags (v2.0/task/bag)
4. Necklaces (v2.0/task/2d-vto/necklace)
5. Earrings (v2.0/task/2d-vto/earring)
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from db import get_db, Selfie, Result, Asset, get_latest_selfie
from auth import get_current_user, create_guest_user
from utils import render, render_partial
from storage import upload_fastapi_file, upload_base64_image, download_and_upload
from youcam_client import (
    CLOTH_VTO, SHOES_VTO, BAG_VTO, NECKLACE_VTO, EARRING_VTO,
    start_task, check_task,
    cloth_vto_payload, shoes_vto_payload, bag_vto_payload,
    necklace_vto_payload, earring_vto_payload
)

router = APIRouter(tags=["style"])
logger = logging.getLogger("styleai.style")

ENDPOINT_MAP = {
    "cloth": CLOTH_VTO,
    "shoes": SHOES_VTO,
    "bag": BAG_VTO,
    "necklace": NECKLACE_VTO,
    "earring": EARRING_VTO,
}


@router.get("/", response_class=HTMLResponse)
async def style_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    user_id = current_user.id if current_user else None
    latest_selfie = get_latest_selfie(db, user_id)

    garment_assets = db.query(Asset).filter(Asset.category == "garment").all()
    shoes_assets = db.query(Asset).filter(Asset.category == "shoes").all()
    bag_assets = db.query(Asset).filter(Asset.category == "bag").all()
    necklace_assets = db.query(Asset).filter(Asset.category == "necklace").all()
    earring_assets = db.query(Asset).filter(Asset.category == "earring").all()

    return render(
        request, "style/index.html", db,
        active_nav="style",
        latest_selfie=latest_selfie,
        garment_assets=garment_assets,
        shoes_assets=shoes_assets,
        bag_assets=bag_assets,
        necklace_assets=necklace_assets,
        earring_assets=earring_assets,
    )


@router.post("/start", response_class=HTMLResponse)
async def style_start(
    request:                 Request,
    db:                      Session               = Depends(get_db),
    tryon_type:              str                   = Form("cloth"), # cloth | shoes | bag | necklace | earring
    selfie_file:             Optional[UploadFile]  = File(None),
    base64_image:            Optional[str]         = Form(None),
    item_asset_url:          Optional[str]         = Form(None),
    custom_item_file:        Optional[UploadFile]  = File(None),
    preset_source_url:       Optional[str]         = Form(None),
    # Feature specific parameters
    garment_category:        str                   = Form("auto"),
    vto_gender:              str                   = Form("female"),
    vto_style:               str                   = Form("random"),
    shadow_intensity:        float                 = Form(0.5),
    ambient_intensity:       float                 = Form(0.5),
    is_right_ear:            bool                  = Form(True),
):
    current_user = get_current_user(request, db)
    if not current_user:
        current_user = create_guest_user(db)
        request.session["user_id"] = current_user.id

    latest_selfie = get_latest_selfie(db, current_user.id)
    src_url = None
    selfie_id = None

    # 1. Determine Source / Model Image
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
        elif preset_source_url and len(preset_source_url) > 10:
            src_url = preset_source_url
        elif latest_selfie:
            src_url = latest_selfie.b2_url
            selfie_id = latest_selfie.id
        else:
            return HTMLResponse('<p class="text-error">No model or portrait photo provided. Please upload or take a photo.</p>', status_code=400)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Photo upload failed: {e}</p>', status_code=500)

    # 2. Determine Product / Item Reference URL
    form_data = await request.form()
    multi_items = form_data.getlist("item_asset_urls")
    if len(multi_items) > 1:
        return await style_batch_start(
            request=request,
            db=db,
            tryon_type=tryon_type,
            selfie_file=selfie_file,
            base64_image=base64_image,
            preset_source_url=preset_source_url,
            garment_category=garment_category,
            vto_gender=vto_gender,
            vto_style=vto_style,
            shadow_intensity=shadow_intensity,
            ambient_intensity=ambient_intensity,
            is_right_ear=is_right_ear,
        )

    ref_url = item_asset_url or (multi_items[0] if multi_items else None)
    if custom_item_file and custom_item_file.filename:
        try:
            b2_item = await upload_fastapi_file(custom_item_file)
            ref_url = b2_item["url"]
        except Exception as e:
            return HTMLResponse(f'<p class="text-error">Item upload failed: {e}</p>', status_code=500)

    if not ref_url:
        return HTMLResponse('<p class="text-error">Please select or upload an item to try on.</p>', status_code=400)

    # 3. Build Endpoint & Payload based on Try-On Category
    endpoint = ENDPOINT_MAP.get(tryon_type, CLOTH_VTO)

    if tryon_type == "shoes":
        payload = shoes_vto_payload(
            src_url=src_url,
            ref_url=ref_url,
            gender=vto_gender,
            style=vto_style,
        )
    elif tryon_type == "bag":
        payload = bag_vto_payload(
            src_url=src_url,
            ref_url=ref_url,
            gender=vto_gender,
            style=vto_style or "style_parisian_chic",
        )
    elif tryon_type == "necklace":
        payload = necklace_vto_payload(
            src_url=src_url,
            ref_url=ref_url,
            shadow_intensity=shadow_intensity,
            ambient_light_intensity=ambient_intensity,
        )
    elif tryon_type == "earring":
        payload = earring_vto_payload(
            src_url=src_url,
            ref_url=ref_url,
            shadow_intensity=shadow_intensity,
            ambient_light_intensity=ambient_intensity,
            is_right_ear=is_right_ear,
        )
    else:  # default: cloth
        payload = cloth_vto_payload(
            src_url=src_url,
            ref_url=ref_url,
            garment_category=garment_category,
        )

    try:
        task_id = await start_task(endpoint, payload)
    except Exception as e:
        logger.error(f"Failed to start {tryon_type} VTO task: {e}")
        return HTMLResponse(f'<p class="text-error">YouCam API error: {e}</p>', status_code=500)

    result = Result(
        user_id=current_user.id,
        selfie_id=selfie_id,
        module=f"tryon_{tryon_type}",
        input_json=json.dumps(payload),
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return render_partial(
        request, "style/partials/polling.html",
        task_id=task_id,
        result_id=result.id,
        tryon_type=tryon_type,
    )


@router.post("/batch/start", response_class=HTMLResponse)
async def style_batch_start(
    request:                 Request,
    db:                      Session               = Depends(get_db),
    tryon_type:              str                   = Form("cloth"),
    selfie_file:             Optional[UploadFile]  = File(None),
    base64_image:            Optional[str]         = Form(None),
    preset_source_url:       Optional[str]         = Form(None),
    garment_category:        str                   = Form("auto"),
    vto_gender:              str                   = Form("female"),
    vto_style:               str                   = Form("random"),
    shadow_intensity:        float                 = Form(0.5),
    ambient_intensity:       float                 = Form(0.5),
    is_right_ear:            bool                  = Form(True),
):
    current_user = get_current_user(request, db)
    if not current_user:
        current_user = create_guest_user(db)
        request.session["user_id"] = current_user.id

    form_data = await request.form()
    ref_urls = form_data.getlist("item_asset_urls")
    if not ref_urls:
        single_ref = form_data.get("item_asset_url")
        if single_ref:
            ref_urls = [single_ref]

    if not ref_urls:
        return HTMLResponse('<p class="text-error">Please select at least 1 item to try on.</p>', status_code=400)

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
        elif preset_source_url and len(preset_source_url) > 10:
            src_url = preset_source_url
        elif latest_selfie:
            src_url = latest_selfie.b2_url
            selfie_id = latest_selfie.id
        else:
            return HTMLResponse('<p class="text-error">No model photo provided.</p>', status_code=400)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Upload failed: {e}</p>', status_code=500)

    # Lookup asset names
    assets_by_url = {
        a.b2_url: a.name for a in db.query(Asset).filter(Asset.b2_url.in_(ref_urls)).all()
    }

    endpoint = ENDPOINT_MAP.get(tryon_type, CLOTH_VTO)
    import asyncio
    import base64 as b64

    async def start_single_vto(url: str, idx: int):
        if tryon_type == "shoes":
            payload = shoes_vto_payload(src_url=src_url, ref_url=url, gender=vto_gender, style=vto_style)
        elif tryon_type == "bag":
            payload = bag_vto_payload(src_url=src_url, ref_url=url, gender=vto_gender, style=vto_style or "style_parisian_chic")
        elif tryon_type == "necklace":
            payload = necklace_vto_payload(src_url=src_url, ref_url=url, shadow_intensity=shadow_intensity, ambient_light_intensity=ambient_intensity)
        elif tryon_type == "earring":
            payload = earring_vto_payload(src_url=src_url, ref_url=url, shadow_intensity=shadow_intensity, ambient_light_intensity=ambient_intensity, is_right_ear=is_right_ear)
        else:
            payload = cloth_vto_payload(src_url=src_url, ref_url=url, garment_category=garment_category)

        name = assets_by_url.get(url, f"{tryon_type.title()} #{idx + 1}")
        try:
            tid = await start_task(endpoint, payload)
            res = Result(
                user_id=current_user.id,
                selfie_id=selfie_id,
                module=f"tryon_{tryon_type}",
                input_json=json.dumps(payload),
            )
            db.add(res)
            db.commit()
            db.refresh(res)
            return {
                "task_id": tid,
                "result_id": res.id,
                "ref_url": url,
                "item_name": name,
                "tryon_type": tryon_type,
                "status": "running",
                "output_url": None,
            }
        except Exception as e:
            return {
                "task_id": None,
                "result_id": None,
                "ref_url": url,
                "item_name": name,
                "tryon_type": tryon_type,
                "status": "error",
                "error": str(e),
                "output_url": None,
            }

    tasks = [start_single_vto(u, i) for i, u in enumerate(ref_urls)]
    items = await asyncio.gather(*tasks)

    batch_json = json.dumps(items)
    batch_data_encoded = b64.urlsafe_b64encode(batch_json.encode()).decode()

    return render_partial(
        request, "style/partials/batch_polling.html",
        items=items,
        batch_data_encoded=batch_data_encoded,
        tryon_type=tryon_type,
    )


@router.get("/batch/status", response_class=HTMLResponse)
async def style_batch_status(
    request:    Request,
    batch_data: str,
    tryon_type: str = "cloth",
    db:         Session = Depends(get_db),
):
    import asyncio
    import base64 as b64

    try:
        raw_json = b64.urlsafe_b64decode(batch_data.encode()).decode()
        items = json.loads(raw_json)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Invalid batch data: {e}</p>', status_code=400)

    endpoint = ENDPOINT_MAP.get(tryon_type, CLOTH_VTO)
    all_done = True

    for item in items:
        if item.get("status") == "running" and item.get("task_id"):
            try:
                res = await check_task(endpoint, item["task_id"])
                task_status = res.get("data", {}).get("task_status")
                if task_status == "success":
                    results_obj = res.get("data", {}).get("results", {})
                    out_url = results_obj.get("url") or results_obj.get("dst_file_url") or results_obj.get("output_url") or results_obj.get("image_url")
                    
                    perm_url = out_url
                    if out_url:
                        try:
                            persisted = await download_and_upload(out_url, prefix=f"styleai/{tryon_type}")
                            perm_url = persisted["url"]
                        except Exception:
                            perm_url = out_url

                    item["status"] = "success"
                    item["output_url"] = perm_url

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
            request, "style/partials/batch_polling.html",
            items=items,
            batch_data_encoded=batch_data_encoded,
            tryon_type=tryon_type,
        )

    successful_items = [i for i in items if i.get("status") == "success" and i.get("output_url")]
    if not successful_items:
        return HTMLResponse(
            '<div class="card" style="border-color:var(--status-error-fg); text-align:center; padding:var(--sp-6);">'
            '<p class="text-error font-bold mb-1">Batch Virtual Try-On Failed</p>'
            '<p class="muted text-xs">Please ensure the target photo has a clear view of the body/face.</p>'
            '</div>'
        )

    return render_partial(
        request, "style/partials/batch_result.html",
        items=successful_items,
        tryon_type=tryon_type,
    )


@router.get("/status/{task_id}", response_class=HTMLResponse)
async def style_status(
    task_id:    str,
    request:    Request,
    db:         Session = Depends(get_db),
    result_id:  int     = 0,
    tryon_type: str     = "cloth",
):
    endpoint = ENDPOINT_MAP.get(tryon_type, CLOTH_VTO)
    try:
        payload = await check_task(endpoint, task_id)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Polling error: {e}</p>', status_code=500)

    status = payload.get("data", {}).get("task_status")

    if status not in ("success", "error"):
        return render_partial(
            request, "style/partials/polling.html",
            task_id=task_id,
            result_id=result_id,
            tryon_type=tryon_type,
        )

    if status == "error":
        err = payload.get("data", {}).get("error", "Unknown error")
        return HTMLResponse(
            f'<div class="card" style="border-color:var(--status-error-fg); padding:var(--sp-4);">'
            f'<p class="text-error">Virtual try-on failed: {err}</p></div>'
        )

    # Success: fetch output image URL
    results_obj = payload.get("data", {}).get("results", {})
    output_url = (
        results_obj.get("url")
        or results_obj.get("dst_file_url")
        or results_obj.get("output_url")
        or results_obj.get("image_url")
    )

    permanent_url = output_url
    if output_url:
        try:
            persisted = await download_and_upload(output_url, prefix=f"styleai/{tryon_type}")
            permanent_url = persisted["url"]
        except Exception as pe:
            logger.warning(f"B2 upload fallback for {tryon_type}: {pe}")
            permanent_url = output_url

    result_obj = db.query(Result).filter(Result.id == result_id).first()
    if result_obj:
        result_obj.result_json = json.dumps(payload)
        result_obj.result_url = permanent_url
        db.commit()

    return render_partial(
        request, "style/partials/result.html",
        output_url=permanent_url,
        tryon_type=tryon_type,
    )

