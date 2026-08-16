"""
Palette module — Facial Color Tone & Season Analysis.
Extracts hex colors for skin, hair, eyes, lips and provides flattering palette recommendations.
"""
import json
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

import logging
from db import get_db, Selfie, Result, get_latest_selfie
from auth import get_current_user, create_guest_user
from utils import render, render_partial
from storage import upload_fastapi_file, upload_base64_image
from youcam_client import SKIN_TONE, start_task, check_task, skin_tone_payload

router = APIRouter(tags=["palette"])
logger = logging.getLogger("styleai.palette")

_ENDPOINT = SKIN_TONE  # "v2.0/task/skin-tone-analysis"


@router.get("/", response_class=HTMLResponse)
async def palette_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    user_id = current_user.id if current_user else None
    latest_selfie = get_latest_selfie(db, user_id)
    return render(request, "palette/index.html", db, active_nav="palette", latest_selfie=latest_selfie)


@router.post("/start", response_class=HTMLResponse)
async def palette_start(
    request:      Request,
    db:           Session               = Depends(get_db),
    selfie_file:  Optional[UploadFile]  = File(None),
    base64_image: Optional[str]         = Form(None),
):
    current_user = get_current_user(request, db)
    if not current_user:
        current_user = create_guest_user(db)
        request.session["user_id"] = current_user.id

    latest_selfie = get_latest_selfie(db, current_user.id)
    src_url = None
    selfie_id = None

    # 1. Upload or use cached image
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
            return HTMLResponse('<p class="text-error">No image provided. Please upload or take a photo.</p>', status_code=400)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">Upload failed: {e}</p>', status_code=500)

    # 3. Start YouCam API task
    try:
        payload = skin_tone_payload(src_url)
        task_id = await start_task(_ENDPOINT, payload)
    except Exception as e:
        return HTMLResponse(f'<p class="text-error">API error: {e}</p>', status_code=500)

    # 4. Save result record
    result = Result(
        user_id=current_user.id,
        selfie_id=selfie_id,
        module="palette",
        input_json=json.dumps({"selfie_url": src_url}),
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return render_partial(
        request, "palette/partials/polling.html",
        task_id=task_id,
        result_id=result.id,
    )


@router.get("/status/{task_id}", response_class=HTMLResponse)
async def palette_status(
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

    if status not in ("success", "error"):
        return render_partial(
            request, "palette/partials/polling.html",
            task_id=task_id,
            result_id=result_id,
        )

    if status == "error":
        err = payload.get("data", {}).get("error", "Unknown error")
        return HTMLResponse(
            f'<div class="card" style="border-color:var(--status-error-fg)">'
            f'<p class="text-error">Color analysis failed: {err}</p></div>'
        )

    # Success
    data_results = payload.get("data", {}).get("results", {})
    
    # Save full result
    result_obj = db.query(Result).filter(Result.id == result_id).first()
    if result_obj:
        result_obj.result_json = json.dumps(payload)
        db.commit()

    # Parse color DNA items with robust schema extraction
    from utils import parse_palette_data
    parsed = parse_palette_data(data_results)
    skin_tone = parsed.get("skin_tone", {})
    hair_color = parsed.get("hair_color", {})
    eye_color = parsed.get("eye_color", {})
    lip_color = parsed.get("lip_color", {})
    undertone = parsed.get("undertone", "Neutral")
    
    # Flattering palette suggestions based on undertone
    palette_recommendations = {
        "Warm": [
            {"name": "Terracotta", "hex": "#c56a3f"},
            {"name": "Golden Olive", "hex": "#8c7b33"},
            {"name": "Warm Amber", "hex": "#d49137"},
            {"name": "Rich Camel", "hex": "#b08556"},
            {"name": "Burnt Peach", "hex": "#d9825b"}
        ],
        "Cool": [
            {"name": "Royal Emerald", "hex": "#2e6f5e"},
            {"name": "Deep Plum", "hex": "#5e2b4c"},
            {"name": "Cobalt Blue", "hex": "#2b4b8a"},
            {"name": "Rose Taupe", "hex": "#8a616b"},
            {"name": "Icy Lavender", "hex": "#a39ec4"}
        ],
        "Neutral": [
            {"name": "Warm Sand", "hex": "#c8b99c"},
            {"name": "Sage Green", "hex": "#6c7a65"},
            {"name": "Dusty Teal", "hex": "#3d6d70"},
            {"name": "Muted Berry", "hex": "#844a5b"},
            {"name": "Espresso", "hex": "#3e2e2b"}
        ]
    }.get(undertone, [
        {"name": "Warm Sand", "hex": "#c8b99c"},
        {"name": "Sage Green", "hex": "#6c7a65"},
        {"name": "Dusty Teal", "hex": "#3d6d70"}
    ])

    return render_partial(
        request, "palette/partials/result.html",
        skin_tone=skin_tone,
        hair_color=hair_color,
        eye_color=eye_color,
        lip_color=lip_color,
        undertone=undertone,
        recommendations=palette_recommendations,
    )
