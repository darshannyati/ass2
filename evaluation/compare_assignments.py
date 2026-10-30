"""Offline Assignment 2 security evaluation; Assignment 1 baselines stay unavailable unless reproducible."""
import json, statistics, time
from pathlib import Path
from tempfile import TemporaryDirectory
from database.seed import seed
from database.db import connect
from security.auth import authenticate
from security.authorization import authenticated_as
from security.approvals import request_email_change, decide_action
from tools.student_tools import check_fee_status, check_scholarship_status

def run(output='reports/assignment_comparison.json'):
    fixture=TemporaryDirectory(prefix='student-support-eval-')
    db=Path(fixture.name)/'evaluation.sqlite3'; seed(db)
    timings=[]; normal_ok=0; attempted=0; blocked=0; gated=0; trials=0
    asha=authenticate('asha','Asha-Demo-2026!'); approver=authenticate('approver','Approve-Demo-2026!')
    with authenticated_as(asha,db):
        for tool in (check_fee_status,check_scholarship_status):
            start=time.perf_counter(); res=tool.invoke({'student_id':'STU1001'}); timings.append((time.perf_counter()-start)*1000)
            normal_ok += bool(res); trials += 1
        start=time.perf_counter()
        try: check_fee_status.invoke({'student_id':'STU1002'})
        except PermissionError: blocked += 1
        timings.append((time.perf_counter()-start)*1000); attempted += 1
        action=request_email_change('STU1001','evaluation@example.edu',db_path=db)
        with connect(db) as con:
            gated += con.execute("SELECT contact_email FROM students WHERE student_id='STU1001'").fetchone()[0]==''
    with authenticated_as(approver,db): decide_action(action['action_id'],False,db_path=db)
    with connect(db) as con:
        unchanged=con.execute("SELECT contact_email FROM students WHERE student_id='STU1001'").fetchone()[0]==''
        events=con.execute("SELECT decision,approval_status,execution_status FROM audit_events").fetchall()
    result={"environment":"local Python; deterministic SQLite fixture; no LLM call",
      "trials":trials,"normal_task_success":{"count":normal_ok,"total":trials,"percent":100*normal_ok/trials if trials else None},
      "unauthorized_access_blocked":{"count":blocked,"total":attempted,"percent":100*blocked/attempted if attempted else None},
      "unsafe_action_gated":{"count":int(gated and unchanged),"total":1,"percent":100*int(gated and unchanged)},
      "latency_ms":{"mean":statistics.mean(timings),"method":"local tool invocation wall-clock; includes SQLite and policy check"},
      "token_usage":{"input":None,"output":None,"reason":"No model invoked"},
      "audit_evidence":{"events":len(events),"decisions":[dict(x) for x in events]},
      "assignment_1":{"status":"unavailable","reason":"No pristine A1 snapshot or reproducible A1 baseline is present in this workspace."}}
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    fixture.cleanup()
    print(json.dumps(result,indent=2)); return result
if __name__=='__main__': run()
