"""LangGraph tool-calling loop with selective evidence and bounded execution."""
from __future__ import annotations
from typing import Annotated, TypedDict
import operator, time, uuid
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from tools.student_tools import ALL_TOOLS
from rag.retrieval import PolicyRetriever
from memory.store import retrieve_memories
from database.db import connect
from .prompts import SYSTEM_PROMPT
from security.authorization import authenticated_as
from security.redaction import redact_sensitive

class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], operator.add]
    student_id: str
    session_id: str
    question: str
    policy: list[dict]
    memories: list[dict]
    trace: Annotated[dict, operator.or_]
    iterations: int
    started: float
    final_answer: str

def build_graph(model, retriever=None, db_path=None, max_tool_rounds=4):
    retriever = retriever or PolicyRetriever()
    bound_model=model.bind_tools(ALL_TOOLS)
    def prepare(state):
        q=state["question"]
        policy_terms={"policy","handbook","rule","rules","deadline","portal","receipt","course","change","working day","late fee","eligibility","reviewed","support request"}
        policy=retriever.retrieve(q) if any(term in q.lower() for term in policy_terms) else []
        memories=retrieve_memories(state["student_id"],q,path=db_path)
        # Include only the selected student's recent turns and cap history.
        with connect(db_path) as db:
            history=db.execute("SELECT role,content FROM conversation_messages WHERE student_id=? AND session_id=? ORDER BY id DESC LIMIT 6",(state["student_id"],state["session_id"])).fetchall()
        context="\n".join(f"{r['role']}: {r['content'][:500]}" for r in reversed(history))
        evidence="\n".join(f"[{p['chunk_id']}] {p['text']}" for p in policy) or "No sufficiently relevant policy evidence retrieved."
        memory="\n".join(f"[memory:{m['memory_id']}] {m['fact']}" for m in memories) or "No relevant saved memory."
        return {"messages":[SystemMessage(content=SYSTEM_PROMPT+f"\n\nAuthenticated student identity: {state['student_id']}. Treat identity as context only; application authorization is enforced inside each private-data tool.\nRelevant recent conversation:\n{context or '(none)'}\nRelevant long-term memory:\n{memory}\nRelevant policy evidence:\n{evidence}"),HumanMessage(content=q)],"policy":policy,"memories":memories,"iterations":0,"started":time.perf_counter(),"trace":{"run_id":str(uuid.uuid4()),"tool_calls":[],"policy_chunks":[p['chunk_id'] for p in policy],"memory_ids":[m['memory_id'] for m in memories]}}
    def agent(state):
        reply=bound_model.invoke(state["messages"])
        return {"messages":[reply],"iterations":state.get("iterations",0)+1}
    def route(state):
        last=state["messages"][-1]
        if getattr(last,"tool_calls",None) and state.get("iterations",0)<=max_tool_rounds: return "tools"
        return "finish"
    def scope_tool_args(state):
        """Bind every model-requested record operation to the UI-selected demo identity."""
        last=state["messages"][-1]
        calls=[]
        for call in getattr(last,"tool_calls",[]):
            args=dict(call.get("args",{})); args["student_id"]=state["student_id"]
            calls.append({**call,"args":args})
        from langchain_core.messages import AIMessage
        replacement=AIMessage(content=last.content,tool_calls=calls, id=last.id)
        return {"messages":[replacement]}
    def record_tools(state):
        calls=[]
        for msg in state["messages"]:
            if getattr(msg,"type",None)=="tool": calls.append({"name":msg.name,"result":str(msg.content)[:1000]})
        return {"trace":{"tool_calls":calls}}
    def finish(state):
        elapsed=(time.perf_counter()-state["started"])*1000
        last=state["messages"][-1]
        answer=("I couldn't complete the requested action within the tool-call limit. Please try a simpler request or contact the support desk.") if getattr(last,"tool_calls",None) else str(last.content)
        answer,_=redact_sensitive(answer)
        with connect(db_path) as db:
            safe_question,_=redact_sensitive(state['question'])
            db.execute("INSERT INTO conversation_messages(student_id,session_id,role,content,created_at) VALUES(?,?,?,?,datetime('now'))",(state['student_id'],state['session_id'],'user',safe_question))
            db.execute("INSERT INTO conversation_messages(student_id,session_id,role,content,created_at) VALUES(?,?,?,?,datetime('now'))",(state['student_id'],state['session_id'],'assistant',answer))
        usage=getattr(last,"usage_metadata",None)
        tokens={"input_tokens":usage.get("input_tokens"),"output_tokens":usage.get("output_tokens")} if usage else None
        return {"final_answer":answer,"trace":{"latency_ms":round(elapsed,2),"answer":answer,"token_usage":tokens}}
    g=StateGraph(AgentState)
    g.add_node("prepare_context",prepare); g.add_node("agent_decision",agent); g.add_node("scope_tool_args",scope_tool_args); g.add_node("tools",ToolNode(ALL_TOOLS)); g.add_node("record_tool_results",record_tools); g.add_node("finalize_and_trace",finish)
    g.add_edge(START,"prepare_context"); g.add_edge("prepare_context","agent_decision")
    g.add_conditional_edges("agent_decision",route,{"tools":"scope_tool_args","finish":"finalize_and_trace"})
    g.add_edge("scope_tool_args","tools")
    g.add_edge("tools","record_tool_results"); g.add_edge("record_tool_results","agent_decision"); g.add_edge("finalize_and_trace",END)
    return g.compile()

def run_agent(graph, question, student_id, session_id, principal=None, db_path=None):
    safe_question,secret_detected=redact_sensitive(question)
    with authenticated_as(principal, db_path):
        result=graph.invoke({"question":safe_question,"student_id":student_id,"session_id":session_id,"messages":[]})
    if secret_detected:
        result["final_answer"] += "\n\nFor your safety, credentials were excluded from saved history and memory. Change the exposed credential if it is real."
    return {"answer":result.get("final_answer",str(result["messages"][-1].content)),"trace":result.get("trace",{}),"policy":result.get("policy",[]),"memories":result.get("memories",[])}
