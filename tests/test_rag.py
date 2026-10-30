from rag.retrieval import PolicyRetriever

def test_relevant_and_unsupported():
    r=PolicyRetriever()
    assert r.retrieve('payment portal unavailable next working day')
    result=r.retrieve('guaranteed GPA scholarship threshold xyzzy')
    assert result and 'does not define a GPA threshold' in result[0]['text']
