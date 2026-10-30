from database.seed import seed
from memory.store import save_memory,list_memories,retrieve_memories,delete_memory

def test_cross_session_persistence_and_delete(tmp_path):
    p=tmp_path/'db.sqlite'; seed(p)
    assert save_memory('STU1001','I prefer concise explanations.',p)['saved']
    got=retrieve_memories('STU1001','How should you explain this?',p)
    assert got and got[0]['fact']=='I prefer concise explanations.'
    assert delete_memory('STU1001',got[0]['memory_id'],p)
    assert not list_memories('STU1001',p)

def test_sensitive_and_temporary_excluded(tmp_path):
    p=tmp_path/'db.sqlite'; seed(p)
    assert not save_memory('STU1001','My password is abc123',p)['saved']
    assert not save_memory('STU1001','Remember this for tomorrow only',p)['saved']
    assert not list_memories('STU1001',p)
