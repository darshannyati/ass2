"""Central policy for record access; tool functions call this themselves."""
from contextvars import ContextVar
from contextlib import contextmanager
from database.db import connect
from observability.audit import audit

_principal: ContextVar[object | None] = ContextVar("student_support_principal", default=None)
_db_path: ContextVar[object | None] = ContextVar("student_support_db_path", default=None)

@contextmanager
def authenticated_as(principal, db_path=None):
    token = _principal.set(principal)
    db_token = _db_path.set(db_path)
    try: yield
    finally:
        _principal.reset(token); _db_path.reset(db_token)

def current_principal(): return _principal.get()

def authorize_student(requested_id: str, action: str, db_path=None, correlation_id="tool"):
    principal = current_principal()
    allowed = bool(principal and principal.role == "student" and principal.student_id == requested_id)
    db_path = db_path or _db_path.get()
    audit(requester_id=getattr(principal,"student_id",None), action=action, target_id="student-record",
          decision="allowed" if allowed else "denied", reason="student_owns_record" if allowed else "student_scope_denied",
          correlation_id=correlation_id, db_path=db_path)
    if not allowed: raise PermissionError("This request cannot be completed for that record.")
    return principal
