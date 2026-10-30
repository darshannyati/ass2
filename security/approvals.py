"""Durable one-shot approval workflow for sensitive contact email changes."""
from datetime import datetime, timezone
import hashlib, json, re, uuid
from database.db import connect
from observability.audit import audit
from .authorization import current_principal

def request_email_change(student_id: str, email: str, *, db_path=None, correlation_id="chat"):
    from .authorization import authorize_student
    principal=authorize_student(student_id,"request_contact_email_change",db_path,correlation_id)
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email)>254:
        raise ValueError("Please provide a valid contact email address.")
    action_id=str(uuid.uuid4()); stamp=datetime.now(timezone.utc).isoformat()
    payload=json.dumps([action_id,principal.student_id,student_id,"contact_email",email],separators=(",",":"))
    digest=hashlib.sha256(payload.encode()).hexdigest()
    with connect(db_path) as db:
        db.execute("INSERT INTO pending_actions VALUES(?,?,?,?,?,?,?, ?,NULL,NULL)",
                   (action_id,principal.student_id,student_id,"contact_email",email,digest,"pending",stamp))
    audit(requester_id=student_id,action="request_contact_email_change",target_id="own-profile",decision="allowed",
          reason="approval_required",correlation_id=correlation_id,approval_required=True,approval_status="pending",db_path=db_path)
    return {"action_id":action_id,"status":"pending","description":"Change your student contact email"}

def decide_action(action_id: str, approve: bool, *, db_path=None, correlation_id="approval"):
    principal=current_principal()
    if not principal or principal.role!="approver":
        audit(requester_id=getattr(principal,"student_id",None),action="decide_sensitive_action",target_id="pending-action",
              decision="denied",reason="approver_role_required",correlation_id=correlation_id,db_path=db_path)
        raise PermissionError("This request cannot be completed.")
    with connect(db_path) as db:
        action=db.execute("SELECT * FROM pending_actions WHERE action_id=?",(action_id,)).fetchone()
        if not action or action["status"]!="pending":
            audit(requester_id=None,action="decide_sensitive_action",target_id="pending-action",decision="denied",
                  reason="invalid_stale_or_replayed_action",correlation_id=correlation_id,db_path=db_path)
            raise ValueError("This approval request is no longer available.")
        payload=json.dumps([action["action_id"],action["requester_id"],action["target_id"],action["field_name"],action["proposed_value"]],separators=(",",":"))
        if not hashlib.sha256(payload.encode()).hexdigest()==action["action_hash"]:
            raise ValueError("This approval request is invalid.")
        status="approved" if approve else "rejected"
        # Conditional update makes the decision one-shot. The protected update occurs in this transaction.
        cur=db.execute("UPDATE pending_actions SET status=?,decided_at=?,approver_id=? WHERE action_id=? AND status='pending'",
                       (status,datetime.now(timezone.utc).isoformat(),principal.username,action_id))
        if cur.rowcount!=1: raise ValueError("This approval request is no longer available.")
        if approve:
            db.execute("UPDATE students SET contact_email=? WHERE student_id=?",(action["proposed_value"],action["target_id"]))
        db.commit()
    audit(requester_id=action["requester_id"],action="execute_contact_email_change",target_id="own-profile",
          decision="allowed",reason="approver_decision",correlation_id=correlation_id,approval_required=True,
          approver_id=principal.username,approval_status=status,execution_status="succeeded" if approve else "cancelled",
          result_summary="Contact email changed" if approve else "Request rejected; record unchanged",db_path=db_path)
    return {"action_id":action_id,"status":status,"message":"Change completed." if approve else "Request rejected; no change was made."}

def pending_actions(db_path=None):
    principal=current_principal()
    if not principal or principal.role!="approver": raise PermissionError("This request cannot be completed.")
    with connect(db_path) as db:
        return [dict(r) for r in db.execute("SELECT action_id,requester_id,target_id,field_name,proposed_value,status,created_at FROM pending_actions WHERE status='pending'")]
