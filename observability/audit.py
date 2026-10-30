"""Sanitized append-only security events persisted in SQLite."""
from datetime import datetime, timezone
import uuid
from database.db import connect

def audit(*, requester_id, action, target_id=None, decision="allowed", reason="policy", correlation_id="system",
          approval_required=False, approver_id=None, approval_status=None, execution_status="not_executed",
          result_summary=None, duration_ms=None, db_path=None):
    with connect(db_path) as db:
        db.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
          (str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), correlation_id, requester_id, action,
           target_id, decision, reason, int(approval_required), approver_id, approval_status,
           execution_status, (result_summary or "")[:200], duration_ms))

def list_audit(limit=100, db_path=None):
    with connect(db_path) as db:
        return [dict(r) for r in db.execute("SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT ?", (limit,))]
