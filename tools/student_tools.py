"""Validated, deterministic operations over the selected demo student's records."""
from __future__ import annotations
from datetime import datetime, timezone
import re
import uuid
from pydantic import BaseModel, Field, field_validator
from langchain_core.tools import tool
from database.db import connect
from security.authorization import authorize_student, _db_path

def _student(db, student_id):
    row = db.execute("SELECT * FROM students WHERE student_id=?", (student_id,)).fetchone()
    if row is None: raise ValueError("Student record not found for the selected demo identity.")
    return row

class StudentInput(BaseModel):
    student_id: str = Field(description="Selected demo student ID")
    @field_validator("student_id")
    @classmethod
    def valid_student(cls, value):
        if not re.fullmatch(r"STU\d{4}", value): raise ValueError("Use a valid demo student ID (STU followed by four digits).")
        return value

class TicketInput(StudentInput):
    category: str = Field(min_length=3, max_length=60)
    description: str = Field(min_length=8, max_length=500)
    @field_validator("category")
    @classmethod
    def valid_category(cls, value):
        if not re.fullmatch(r"[A-Za-z][A-Za-z &-]{2,59}", value): raise ValueError("Invalid ticket category.")
        return value.strip()

class TicketStatusInput(StudentInput):
    ticket_id: str = Field(min_length=12, max_length=12, description="Ticket ID returned when request was created")
    @field_validator("ticket_id")
    @classmethod
    def valid_ticket(cls, value):
        if not re.fullmatch(r"TKT-[A-F0-9]{8}", value): raise ValueError("Invalid ticket ID format.")
        return value

def check_fee_status_impl(student_id, path=None):
    with connect(path) as db:
        row = _student(db, student_id)
        return {"student_id": student_id, "fee_amount": row["fee_amount"], "amount_paid": row["amount_paid"],
                "outstanding_balance": round(row["fee_amount"]-row["amount_paid"],2), "payment_status": row["payment_status"]}

def check_scholarship_status_impl(student_id, path=None):
    with connect(path) as db:
        row = _student(db, student_id)
        return {"student_id": student_id, "status": row["scholarship_status"], "eligibility_information": row["scholarship_eligibility"]}

def create_support_request_impl(student_id, category, description, path=None):
    from security.redaction import redact_sensitive
    category,_=redact_sensitive(category); description,_=redact_sensitive(description)
    with connect(path) as db:
        _student(db, student_id)
        ticket_id = "TKT-" + uuid.uuid4().hex[:8].upper()
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        db.execute("INSERT INTO tickets VALUES(?,?,?,?,?,?)", (ticket_id, student_id, category, description, "open", created))
        return {"ticket_id": ticket_id, "category": category, "status": "open", "created_at": created}

def check_support_request_status_impl(student_id, ticket_id, path=None):
    with connect(path) as db:
        row=db.execute("SELECT ticket_id,category,status,created_at FROM tickets WHERE ticket_id=? AND student_id=?",(ticket_id,student_id)).fetchone()
        if not row: raise ValueError("Ticket not found for the selected demo identity.")
        return dict(row)

@tool(args_schema=StudentInput)
def check_fee_status(student_id: str) -> dict:
    """Check the selected student's fee total, amount paid, balance, and status."""
    authorize_student(student_id, "check_fee_status")
    result=check_fee_status_impl(student_id, _db_path.get())
    from observability.audit import audit
    audit(requester_id=student_id,action="check_fee_status",target_id="student-record",decision="allowed",reason="execution_completed",execution_status="succeeded",db_path=_db_path.get())
    return result

@tool(args_schema=StudentInput)
def check_scholarship_status(student_id: str) -> dict:
    """Check the selected student's scholarship application status and recorded eligibility information."""
    authorize_student(student_id, "check_scholarship_status")
    result=check_scholarship_status_impl(student_id, _db_path.get())
    from observability.audit import audit
    audit(requester_id=student_id,action="check_scholarship_status",target_id="student-record",decision="allowed",reason="execution_completed",execution_status="succeeded",db_path=_db_path.get())
    return result

@tool(args_schema=TicketInput)
def create_support_request(student_id: str, category: str, description: str) -> dict:
    """Create a support request for the selected student and return its persisted ticket ID."""
    authorize_student(student_id, "create_support_request")
    result=create_support_request_impl(student_id, category, description, _db_path.get())
    from observability.audit import audit
    audit(requester_id=student_id,action="create_support_request",target_id="support-request",decision="allowed",reason="execution_completed",execution_status="succeeded",db_path=_db_path.get())
    return result

@tool(args_schema=TicketStatusInput)
def check_support_request_status(student_id: str, ticket_id: str) -> dict:
    """Check a support ticket belonging to the selected student identity."""
    authorize_student(student_id, "check_support_request_status")
    result=check_support_request_status_impl(student_id,ticket_id,_db_path.get())
    from observability.audit import audit
    audit(requester_id=student_id,action="check_support_request_status",target_id="support-request",decision="allowed",reason="execution_completed",execution_status="succeeded",db_path=_db_path.get())
    return result

ALL_TOOLS = [check_fee_status, check_scholarship_status, create_support_request, check_support_request_status]
