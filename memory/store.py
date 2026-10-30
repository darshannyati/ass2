"""SQLite-backed inspectable long-term memory, separate from conversation history."""
from datetime import datetime, timezone
from database.db import connect
from .policies import classify_memory

def save_memory(student_id: str, text: str, path=None):
    allowed, reason = classify_memory(text)
    if not allowed: return {"saved": False, "reason": reason}
    with connect(path) as db:
        db.execute("INSERT OR IGNORE INTO memories(student_id,fact,category,created_at) VALUES(?,?,?,?)",
          (student_id,text.strip(),"preference_or_study_context",datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return {"saved": True, "reason": reason}

def list_memories(student_id, path=None):
    with connect(path) as db:
        return [dict(r) for r in db.execute("SELECT memory_id,fact,category,created_at FROM memories WHERE student_id=? ORDER BY memory_id",(student_id,))]

def retrieve_memories(student_id, query, path=None, limit=3):
    def stem(word):
        word=word.lower()
        if word.startswith("explanat") or word.startswith("explana"): return "explain"
        if word.startswith("preferen"): return "prefer"
        for suffix in ("ations","ation","ments","ment","ingly","edly","ing","ies","es","s"):
            if len(word)>len(suffix)+3 and word.endswith(suffix):
                return word[:-len(suffix)]+("y" if suffix=="ies" else "")
        return word
    words={stem(w) for w in query.split() if len(w)>3}
    rows=list_memories(student_id,path)
    def matches(a,b): return a==b or (len(a)>4 and len(b)>4 and (a.startswith(b) or b.startswith(a)))
    ranked=sorted(rows,key=lambda x:sum(any(matches(w,t) for t in {stem(t) for t in x["fact"].split()}) for w in words),reverse=True)
    relevant=[r for r in ranked if any(matches(w,t) for t in {stem(t) for t in r["fact"].split()} for w in words)]
    return relevant[:limit]

def delete_memory(student_id, memory_id, path=None):
    with connect(path) as db:
        cur=db.execute("DELETE FROM memories WHERE memory_id=? AND student_id=?",(memory_id,student_id))
        return cur.rowcount==1
