"""
Shared template renderer — injects current_user + flash messages into every response.
"""
from pathlib import Path
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from auth import get_current_user, pop_flash

_TMPL_DIR = Path(__file__).parent / "templates"
templates  = Jinja2Templates(directory=str(_TMPL_DIR))


def render(request, template_name: str, db: Session, active_nav: str = "", **ctx):
    """
    Render a Jinja2 template with standard context injected:
      - current_user
      - flash_messages
      - active_nav (sidebar highlight)

    Usage in route handler:
        return render(request, "skin/index.html", db, active_nav="skin")
    """
    current_user   = get_current_user(request, db)
    flash_messages = pop_flash(request)

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "current_user":   current_user,
            "flash_messages": flash_messages,
            "active_nav":     active_nav,
            **ctx,
        },
    )


def render_partial(request, template_name: str, **ctx):
    """
    Render a partial template (no common context needed — used in HTMX swaps).
    """
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=ctx,
    )


def format_api_error(err: str) -> str:
    """Format raw YouCam error codes into user-friendly guidance."""
    if not err:
        return "An unknown error occurred. Please try again."
    err_lower = str(err).lower()
    if "error_download_image" in err_lower:
        return "Image validation failed: The photo may be too small or low-resolution (minimum 480px required). Please upload a clearer, standard photo."
    if "face" in err_lower:
        return "Face not detected: Please ensure the face is clearly visible, well-lit, and forward-facing."
    return f"Processing failed ({err}). Please try again with a different photo."


def parse_palette_data(data_results: dict) -> dict:
    """
    Parses YouCam skin-tone-analysis output into structured dictionary.
    Handles both {results: {color: {...}}} and {results: {skin_tone: {...}}} schemas.
    """
    if not isinstance(data_results, dict):
        return {}

    color_obj = data_results.get("color", {})
    
    # 1. Skin Tone
    skin_hex = color_obj.get("skin_color") or data_results.get("skin_tone", {}).get("hex") or "#d9a37e"
    skin_tone = {
        "hex": skin_hex,
        "pantone": data_results.get("skin_tone", {}).get("pantone")
    }

    # 2. Hair Color
    hair_hex = color_obj.get("hair_color") or data_results.get("hair_color", {}).get("hex") or "#3b2f2f"
    hair_name = color_obj.get("hair_color_name") or data_results.get("hair_color", {}).get("name")
    hair_color = {"hex": hair_hex, "name": hair_name}

    # 3. Eye Color
    eye_hex = color_obj.get("eye_color") or data_results.get("eye_color", {}).get("hex") or "#4a3b32"
    eye_name = color_obj.get("eye_color_name") or data_results.get("eye_color", {}).get("name")
    eye_color = {"hex": eye_hex, "name": eye_name}

    # 4. Lip Color
    lip_hex = color_obj.get("lip_color") or data_results.get("lip_color", {}).get("hex") or "#b85d68"
    lip_color = {"hex": lip_hex}

    # 5. Undertone Detection
    raw_undertone = data_results.get("skin_tone", {}).get("undertone") or color_obj.get("undertone")
    if raw_undertone:
        undertone = raw_undertone.capitalize()
    else:
        try:
            hex_clean = skin_hex.lstrip("#")
            r = int(hex_clean[0:2], 16)
            g = int(hex_clean[2:4], 16)
            b = int(hex_clean[4:6], 16)
            if r > g > b and (r - b) > 35:
                undertone = "Warm"
            elif b > g or (r - g) < 15:
                undertone = "Cool"
            else:
                undertone = "Neutral"
        except Exception:
            undertone = "Neutral"

    return {
        "skin_tone": skin_tone,
        "hair_color": hair_color,
        "eye_color": eye_color,
        "lip_color": lip_color,
        "undertone": undertone,
    }


