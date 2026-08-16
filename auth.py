"""
Auth utilities — password hashing, guest creation, session flash helpers.
Uses bcrypt directly (passlib incompatible with bcrypt 5.x on Python 3.14+).
"""
import uuid
import bcrypt
from sqlalchemy.orm import Session
from db import User


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def get_current_user(request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def create_guest_user(db: Session) -> User:
    user = User(
        username=f"guest_{uuid.uuid4().hex[:6]}",
        is_guest=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ─── Flash messages ───────────────────────────────────────────────────────────

def set_flash(request, text: str, kind: str = "info"):
    """kinds: info | success | error | warning"""
    msgs = request.session.get("flashes", [])
    msgs.append({"text": text, "kind": kind})
    request.session["flashes"] = msgs


def pop_flash(request) -> list:
    msgs = request.session.get("flashes", [])
    request.session["flashes"] = []
    return msgs
