"""Summarize a generated CSV report without inventing model scores."""
import csv
from pathlib import Path
def summarize(path="reports/evaluation.csv"):
    rows=list(csv.DictReader(Path(path).open(encoding="utf-8")))
    return {"cases":len(rows),"success_rate":sum(r['success']=='True' for r in rows)/max(1,len(rows)),"mean_latency_ms":sum(float(r['latency_ms']) for r in rows)/max(1,len(rows)),"token_usage_available":any(r['input_tokens'] or r['output_tokens'] for r in rows)}
