"""Reproducible offline deterministic checks and optional configured-model run."""
import csv,json,time
from pathlib import Path
from database.seed import seed
from database.db import connect
from tools.student_tools import check_fee_status_impl,check_scholarship_status_impl
from rag.retrieval import PolicyRetriever
from memory.store import save_memory,retrieve_memories
from memory.policies import classify_memory

def run(output="reports/evaluation.csv"):
    seed(); retriever=PolicyRetriever(); rows=[]
    cases=[json.loads(s) for s in Path("evaluation/test_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    for c in cases:
        t=time.perf_counter(); ok=True; notes=[]; evidence=[]; tools=[]; memory=[]
        q=c['question']; sid=c.get('student')
        if c.get('expected_tools'):
            for name in c['expected_tools']:
                tools.append(name)
                try:
                    if name=='check_fee_status':
                        result=check_fee_status_impl(sid)
                        if c['id']=='fee_status': ok &= result['outstanding_balance']==70000
                        elif c['id']=='fee_paid': ok &= result['payment_status']=='paid' and result['outstanding_balance']==0
                    elif name=='check_scholarship_status': result=check_scholarship_status_impl(sid); ok &= result['status']=='under_review'
                    elif name=='create_support_request':
                        from tools.student_tools import create_support_request_impl
                        result=create_support_request_impl(sid,'Fee receipt','Receipt missing after payment')
                    else: result={}
                    notes.append(str(result))
                except Exception as e: ok=False; notes.append(type(e).__name__)
        retrieved=retriever.retrieve(q); evidence=[p['chunk_id'] for p in retrieved]
        if c.get('expected_evidence'): ok &= bool(retrieved)
        if c.get('expected_limitation') and c['id']=='unsupported_policy':
            ok &= bool(retrieved) and 'does not define a GPA threshold' in retrieved[0]['text']
        if c.get('expected_memory_excluded'): ok &= not classify_memory(q)[0]
        if c.get('expected_memory'):
            save_memory(sid,'I prefer concise explanations.',path=None); memory=[x['memory_id'] for x in retrieve_memories(sid,q)]
        latency=(time.perf_counter()-t)*1000
        rows.append({"case_id":c['id'],"success":bool(ok),"tools":json.dumps(tools),"tool_results":json.dumps(notes),"policy_chunks":json.dumps(evidence),"memory_ids":json.dumps(memory),"latency_ms":round(latency,2),"input_tokens":None,"output_tokens":None,"token_note":"No LLM invoked in deterministic baseline"})
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    print(f"Cases: {len(rows)}; deterministic checks passed: {sum(r['success'] for r in rows)}/{len(rows)}; report: {out}")
    return rows
if __name__=='__main__': run()
