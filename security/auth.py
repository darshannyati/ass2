"""Small demo authentication layer. Replace demo accounts with campus SSO in production."""
from __future__ import annotations
import hashlib, hmac, os
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
from database.db import connect

_DEMO = {"asha": ("STU1001", "student"), "kabir": ("STU1002", "student"),
         "mira": ("STU1003", "student"), "approver": (None, "approver")}
_PASSWORDS = {"asha": "Asha-Demo-2026!", "kabir": "Kabir-Demo-2026!",
              "mira": "Mira-Demo-2026!", "approver": "Approve-Demo-2026!"}
_SALT = b"student-support-assignment-demo"
_HASHES = {u: hashlib.pbkdf2_hmac("sha256", p.encode(), _SALT, 200_000) for u,p in _PASSWORDS.items()}

@dataclass(frozen=True)
class Principal:
    username: str
    role: str
    student_id: str | None

def authenticate(username: str, password: str) -> Principal | None:
    username = username.strip().lower()
    record = _DEMO.get(username)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), _SALT, 200_000)
    if not record or not hmac.compare_digest(candidate, _HASHES[username]):
        return None
    return Principal(username, record[1], record[0])

def record_login(principal: Principal, db_path=None) -> None:
    """Persist a successful demo login without storing credentials or session data."""
    with connect(db_path) as db:
        db.execute(
            "INSERT INTO login_events VALUES(?,?,?,?,?)",
            (str(uuid.uuid4()), principal.username, principal.role, principal.student_id,
             datetime.now(timezone.utc).isoformat()),
        )
