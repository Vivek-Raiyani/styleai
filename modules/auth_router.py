from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from db import get_db, User
from auth import hash_password, verify_password, create_guest_user, set_flash
from utils import render

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    return render(request, "auth/login.html", db, active_nav="")


@router.post("/login")
async def login_submit(
    request: Request,
    email: str    = Form(...),
    password: str = Form(...),
    db: Session   = Depends(get_db),
):
    # Allow logging in with either email or username
    login_str = email.strip()
    user = db.query(User).filter((User.email == login_str) | (User.username == login_str)).first()
    if not user or not verify_password(password, user.password_hash):
        set_flash(request, "Invalid email/username or password.", "error")
        return RedirectResponse("/auth/login", status_code=303)
    request.session["user_id"] = user.id
    set_flash(request, f"Welcome back, {user.username}!", "success")
    return RedirectResponse("/admin" if user.is_admin else "/", status_code=303)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    return render(request, "auth/register.html", db, active_nav="")


@router.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    email: str    = Form(...),
    password: str = Form(...),
    db: Session   = Depends(get_db),
):
    if db.query(User).filter(User.email == email).first():
        set_flash(request, "Email already registered.", "error")
        return RedirectResponse("/auth/register", status_code=303)
    if db.query(User).filter(User.username == username).first():
        set_flash(request, "Username taken, try another.", "error")
        return RedirectResponse("/auth/register", status_code=303)

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_guest=False,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    request.session["user_id"] = user.id
    set_flash(request, "Account created! Welcome to StyleAI Studio.", "success")
    return RedirectResponse("/", status_code=303)


@router.get("/guest")
async def login_guest(request: Request, db: Session = Depends(get_db)):
    user = create_guest_user(db)
    request.session["user_id"] = user.id
    set_flash(request, "You're browsing as a guest. Results are saved to your session.", "info")
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
