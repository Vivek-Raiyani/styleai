"""
YouCam Makeup API — async httpx client.
Pattern: start_task() → poll check_task() until success/error.
"""
import os
import asyncio
import json
import httpx
from dotenv import load_dotenv

import logging

load_dotenv()

logger = logging.getLogger("styleai.youcam")

_BASE  = "https://yce-api-01.makeupar.com/s2s"


def get_headers() -> dict:
    token = os.getenv("YCE_TOKEN", "")
    if not token:
        logger.warning("YCE_TOKEN environment variable is not configured. YouCam API calls may fail.")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

# ─── API Endpoint constants ────────────────────────────────────────────────────
SKIN_ANALYSIS   = "v2.1/task/skin-analysis"
SKIN_TONE       = "v2.0/task/skin-tone-analysis"
HAIR_COLOR      = "v2.0/task/hair-color"
HAIR_TRANSFER   = "v2.1/task/hair-transfer"
EYE_LENS        = "v2.0/task/eye-color-vto"
CLOTH_VTO       = "v2.0/task/cloth-v4"
SHOES_VTO       = "v2.0/task/shoes"
BAG_VTO         = "v2.0/task/bag"
NECKLACE_VTO    = "v2.0/task/2d-vto/necklace"
EARRING_VTO     = "v2.0/task/2d-vto/earring"


# ─── Core helpers ─────────────────────────────────────────────────────────────

async def start_task(endpoint: str, payload: dict) -> str:
    """POST to start an async task. Returns task_id."""
    url = f"{_BASE}/{endpoint}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=get_headers(), json=payload)
        r.raise_for_status()
        data = r.json()
    task_id = data.get("data", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in response: {json.dumps(data)}")
    return task_id


async def check_task(endpoint: str, task_id: str) -> dict:
    """Single GET poll. Returns full API payload. Check data.task_status yourself."""
    url = f"{_BASE}/{endpoint}/{task_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=get_headers())
        r.raise_for_status()
        return r.json()


async def run_task(endpoint: str, payload: dict,
                   interval: float = 2.0, max_tries: int = 150) -> dict:
    """
    Convenience: start + poll until success or error.
    Returns full success payload. Raises on error or timeout.
    Use this only in background tasks (not in request handlers).
    """
    task_id = await start_task(endpoint, payload)
    for _ in range(max_tries):
        result = await check_task(endpoint, task_id)
        status = result.get("data", {}).get("task_status")
        if status == "success":
            return result
        if status == "error":
            raise RuntimeError(f"YouCam task error: {json.dumps(result)}")
        await asyncio.sleep(interval)
    raise RuntimeError(f"Timeout waiting for task {task_id}")


# ─── Feature-specific payload builders ────────────────────────────────────────

def skin_analysis_payload(src_url: str, actions: list[str] | None = None) -> dict:
    if actions is None:
        actions = [
            "acne", "firmness", "radiance", "tear_trough", "skin_type",
            "texture", "redness", "pore", "moisture", "eye_bag",
            "droopy_lower_eyelid", "dark_circle_v2", "droopy_upper_eyelid",
            "oiliness", "age_spot", "wrinkle",
        ]
    return {
        "src_file_url": src_url,
        "dst_actions": actions,
        "miniserver_args": {"enable_mask_overlay": False},
        "format": "json",
        "pf_camera_kit": False,
    }


def skin_tone_payload(src_url: str) -> dict:
    return {"src_file_url": src_url}


def hair_color_payload(src_url: str, color: str,
                        pattern: str = "full",
                        second_color: str | None = None,
                        color_intensity: int = 50,
                        shine_intensity: int = 50,
                        blend_strength: int = 100,
                        coloring_section: str = "top") -> dict:
    palettes = [{"color": color, "color_intensity": color_intensity, "shine_intensity": shine_intensity}]
    if pattern == "ombre" and second_color:
        palettes.append({"color": second_color, "color_intensity": color_intensity, "shine_intensity": shine_intensity})

    payload: dict = {"src_file_url": src_url, "palettes": palettes}
    if pattern == "ombre":
        payload["pattern"] = {
            "name": "ombre",
            "blend_strength": blend_strength,
            "line_offset": 0,
            "coloring_section": coloring_section,
        }
    else:
        payload["pattern"] = {"name": "full"}
    return payload


def hair_transfer_payload(src_url: str, ref_url: str) -> dict:
    return {"src_file_url": src_url, "ref_file_url": ref_url}


def eye_lens_payload(src_url: str, lens_url: str,
                      intensity: int = 50, enlargement: int = 0,
                      smooth_strength: int = 50, smooth_color: int = 50) -> dict:
    return {
        "src_file_url": src_url,
        "ref_file_url": lens_url,
        "effect": {
            "intensity": intensity,
            "enlargement": enlargement,
            "skin_smooth_strength": smooth_strength,
            "skin_smooth_color_intensity": smooth_color,
        },
        "version": "1.0",
    }


def cloth_vto_payload(src_url: str, ref_url: str,
                       garment_category: str = "auto") -> dict:
    valid_categories = {"auto", "upper_body", "lower_body", "dresses"}
    cat = garment_category.lower() if garment_category else "auto"
    if cat not in valid_categories:
        cat = "auto"
    return {
        "src_file_url": src_url,
        "ref_file_url": ref_url,
        "garment_category": cat,
    }


def shoes_vto_payload(src_url: str, ref_url: str,
                      gender: str = "female",
                      style: str = "random") -> dict:
    return {
        "src_file_url": src_url,
        "ref_file_url": ref_url,
        "gender": gender.lower() if gender in ("female", "male") else "female",
        "style": style or "random",
    }


def bag_vto_payload(src_url: str, ref_url: str,
                    gender: str = "female",
                    style: str = "style_parisian_chic") -> dict:
    return {
        "src_file_url": src_url,
        "ref_file_url": ref_url,
        "gender": gender.lower() if gender in ("female", "male") else "female",
        "style": style or "style_parisian_chic",
    }


def necklace_vto_payload(src_url: str, ref_url: str,
                         shadow_intensity: float = 0.5,
                         ambient_light_intensity: float = 0.5,
                         need_remove_background: bool = False) -> dict:
    return {
        "src_file_url": src_url,
        "source_info": {
            "name": src_url
        },
        "ref_file_urls": [ref_url],
        "ref_file_ids": [],
        "object_infos": [
            {
                "name": ref_url,
                "parameter": {
                    "necklace_need_remove_background": need_remove_background,
                    "necklace_shadow_intensity": float(shadow_intensity),
                    "necklace_ambient_light_intensity": float(ambient_light_intensity),
                }
            }
        ]
    }


def earring_vto_payload(src_url: str, ref_url: str,
                        shadow_intensity: float = 0.3,
                        ambient_light_intensity: float = 1.0,
                        is_right_ear: bool = True,
                        occluded_type: int = 0,
                        need_remove_background: bool = False) -> dict:
    return {
        "src_file_url": src_url,
        "source_info": {
            "name": src_url
        },
        "ref_file_urls": [ref_url],
        "ref_file_ids": [],
        "refmsk_file_urls": [],
        "refmsk_file_ids": [],
        "object_infos": [
            {
                "name": ref_url,
                "parameter": {
                    "earring_need_remove_background": need_remove_background,
                    "earring_shadow_intensity": float(shadow_intensity),
                    "earring_ambient_light_intensity": float(ambient_light_intensity),
                    "earring_occluded_type": int(occluded_type),
                    "earring_is_right_ear": bool(is_right_ear),
                }
            }
        ]
    }
