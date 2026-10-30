"""Append-only JSONL traces with no credentials or raw model prompts."""
import json, os
from pathlib import Path
from datetime import datetime, timezone
from security.redaction import redact_sensitive

def write_trace(trace, question, answer, test_case_id=None, expected=None):
    question,_=redact_sensitive(question); answer,_=redact_sensitive(answer)
    root=Path(os.getenv("STUDENT_AGENT_TRACE_DIR","reports/traces")); root.mkdir(parents=True,exist_ok=True)
    item={"timestamp":datetime.now(timezone.utc).isoformat(),"test_case_id":test_case_id,"question":question[:1000],"expected":expected,"answer":answer[:2000],**trace}
    with (root/"runs.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(item,ensure_ascii=False)+"\n")
