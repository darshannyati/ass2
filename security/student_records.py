"""Role-scoped read access to student records and activity history."""
from database.db import connect


def _scope(principal):
    if not principal or principal.role not in {"student", "approver"}:
        raise PermissionError("This request cannot be completed.")
    if principal.role == "student" and not principal.student_id:
        raise PermissionError("This request cannot be completed.")
    return principal.student_id if principal.role == "student" else None


def list_student_records(principal, db_path=None):
    student_id = _scope(principal)
    with connect(db_path) as db:
        query = """SELECT student_id, display_name, programme, semester, contact_email
                   FROM students"""
        params = ()
        if student_id:
            query += " WHERE student_id=?"
            params = (student_id,)
        return [dict(row) for row in db.execute(query + " ORDER BY student_id", params)]


def list_email_change_history(principal, db_path=None):
    student_id = _scope(principal)
    query = """SELECT action_id, requester_id, target_id, proposed_value, status,
                      created_at, decided_at, approver_id
               FROM pending_actions WHERE field_name='contact_email'"""
    params = ()
    if student_id:
        query += " AND target_id=?"
        params = (student_id,)
    with connect(db_path) as db:
        return [dict(row) for row in db.execute(query + " ORDER BY created_at DESC", params)]


def list_login_history(principal, db_path=None):
    student_id = _scope(principal)
    query = """SELECT username, role, student_id, logged_in_at
               FROM login_events"""
    params = ()
    if student_id:
        query += " WHERE student_id=?"
        params = (student_id,)
    with connect(db_path) as db:
        return [dict(row) for row in db.execute(query + " ORDER BY logged_in_at DESC", params)]
