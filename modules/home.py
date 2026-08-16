from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from db import get_db, Result, Selfie
from auth import get_current_user
from utils import render

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)

    recent_results = []
    if current_user:
        recent_results = (
            db.query(Result)
            .filter(Result.user_id == current_user.id)
            .order_by(Result.created_at.desc())
            .limit(8)
            .all()
        )

    return render(
        request, "home/index.html", db,
        active_nav="home",
        recent_results=recent_results,
    )
