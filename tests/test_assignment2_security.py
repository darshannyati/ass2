import sqlite3
import pytest
from database.seed import seed
from database.db import connect
from security.auth import Principal, authenticate, record_login
from security.authorization import authenticated_as
from security.approvals import request_email_change, decide_action
from security.student_records import list_student_records, list_email_change_history, list_login_history
from security.redaction import redact_sensitive
from memory.store import save_memory, list_memories
from tools.student_tools import check_fee_status

def test_authenticated_self_access_and_direct_tool_cross_student_denial(tmp_path):
    p=tmp_path/'app.db'; seed(p)
    asha=authenticate('asha','Asha-Demo-2026!')
    with authenticated_as(asha,p):
        assert check_fee_status.invoke({'student_id':'STU1001'})['outstanding_balance']==70000
        with pytest.raises(PermissionError): check_fee_status.invoke({'student_id':'STU1002'})
    with connect(p) as db:
        events=db.execute("SELECT decision,execution_status FROM audit_events").fetchall()
    assert sum(x['decision']=='denied' for x in events)==1
    assert sum(x['execution_status']=='succeeded' for x in events)==1

def test_sensitive_action_requires_approver_and_rejection_has_no_effect(tmp_path):
    p=tmp_path/'app.db'; seed(p); asha=authenticate('asha','Asha-Demo-2026!')
    with authenticated_as(asha): pending=request_email_change('STU1001','new@example.edu',db_path=p)
    with connect(p) as db: assert db.execute("SELECT contact_email FROM students WHERE student_id='STU1001'").fetchone()[0]==''
    with authenticated_as(asha), pytest.raises(PermissionError): decide_action(pending['action_id'],True,db_path=p)
    approver=authenticate('approver','Approve-Demo-2026!')
    with authenticated_as(approver): result=decide_action(pending['action_id'],False,db_path=p)
    assert result['status']=='rejected'
    with connect(p) as db:
        assert db.execute("SELECT contact_email FROM students WHERE student_id='STU1001'").fetchone()[0]==''
        assert db.execute("SELECT status FROM pending_actions WHERE action_id=?",(pending['action_id'],)).fetchone()[0]=='rejected'
    with authenticated_as(approver), pytest.raises(ValueError): decide_action(pending['action_id'],True,db_path=p)

def test_approval_executes_once_and_updates_only_own_record(tmp_path):
    p=tmp_path/'app.db'; seed(p); asha=authenticate('asha','Asha-Demo-2026!')
    with authenticated_as(asha): pending=request_email_change('STU1001','new@example.edu',db_path=p)
    with authenticated_as(authenticate('approver','Approve-Demo-2026!')):
        assert decide_action(pending['action_id'],True,db_path=p)['status']=='approved'
        with pytest.raises(ValueError): decide_action(pending['action_id'],True,db_path=p)
    with connect(p) as db: assert db.execute("SELECT contact_email FROM students WHERE student_id='STU1001'").fetchone()[0]=='new@example.edu'

def test_student_records_and_activity_are_role_scoped(tmp_path):
    p=tmp_path/'app.db'; seed(p)
    asha=authenticate('asha','Asha-Demo-2026!')
    kabir=authenticate('kabir','Kabir-Demo-2026!')
    approver=authenticate('approver','Approve-Demo-2026!')
    record_login(asha,p)
    record_login(kabir,p)
    with authenticated_as(asha,p): request_email_change('STU1001','asha.new@example.edu',db_path=p)

    assert [row['student_id'] for row in list_student_records(asha,p)]==['STU1001']
    assert [row['student_id'] for row in list_student_records(approver,p)]==['STU1001','STU1002','STU1003']
    with pytest.raises(PermissionError):
        list_student_records(Principal('invalid','student',None),p)
    assert len(list_email_change_history(asha,p))==1
    assert list_email_change_history(kabir,p)==[]
    assert [row['student_id'] for row in list_login_history(asha,p)]==['STU1001']
    assert len(list_login_history(approver,p))==2

def test_otp_password_redacted_and_never_persisted(tmp_path):
    p=tmp_path/'app.db'; seed(p)
    message='My password is Swordfish123 and OTP 483920'
    cleaned,detected=redact_sensitive(message)
    assert detected and 'Swordfish123' not in cleaned and '483920' not in cleaned
    assert not save_memory('STU1001',message,p)['saved']
    assert list_memories('STU1001',p)==[]
