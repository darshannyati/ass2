import pytest
from database.seed import seed
from tools.student_tools import check_fee_status_impl,check_scholarship_status_impl,create_support_request_impl,check_support_request_status_impl,StudentInput

def test_fee_and_scholarship(tmp_path):
    p=tmp_path/'db.sqlite'; seed(p)
    assert check_fee_status_impl('STU1001',p)['outstanding_balance']==70000
    assert check_scholarship_status_impl('STU1001',p)['status']=='under_review'

def test_unknown_student_and_validation(tmp_path):
    p=tmp_path/'db.sqlite'; seed(p)
    with pytest.raises(ValueError): check_fee_status_impl('STU9999',p)
    with pytest.raises(Exception): StudentInput(student_id='other')

def test_ticket_persists_and_scopes_to_student(tmp_path):
    p=tmp_path/'db.sqlite'; seed(p)
    ticket=create_support_request_impl('STU1001','Fees','My receipt is missing',p)
    assert check_support_request_status_impl('STU1001',ticket['ticket_id'],p)['status']=='open'
    with pytest.raises(ValueError): check_support_request_status_impl('STU1002',ticket['ticket_id'],p)
