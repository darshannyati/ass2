from langchain_core.messages import AIMessage
from database.seed import seed
from agent.graph import build_graph,run_agent
from rag.retrieval import PolicyRetriever
from security.auth import authenticate

class FakeModel:
    def __init__(self): self.calls=0
    def bind_tools(self,tools): return self
    def invoke(self,messages):
        self.calls+=1
        if self.calls==1:
            return AIMessage(content="",tool_calls=[{"name":"check_fee_status","args":{"student_id":"STU1002"},"id":"call-1","type":"tool_call"}])
        tool_result=next(m.content for m in reversed(messages) if getattr(m,"type",None)=="tool")
        return AIMessage(content=f"Fee result: {tool_result}")

def test_agent_tool_loop_scopes_selected_identity_and_records_trace(tmp_path):
    db=tmp_path/'db.sqlite'; seed(db)
    graph=build_graph(FakeModel(),PolicyRetriever(),db_path=db)
    result=run_agent(graph,'What is my fee status?','STU1001','session-a',authenticate('asha','Asha-Demo-2026!'),db_path=db)
    assert '70000' in result['answer']
    assert result['trace']['tool_calls'][0]['name']=='check_fee_status'
    assert result['trace']['policy_chunks']==[]
