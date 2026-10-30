import os
from dotenv import load_dotenv

load_dotenv()

def get_chat_model():
    provider=os.getenv("STUDENT_AGENT_PROVIDER","groq").lower()
    model=os.getenv("STUDENT_AGENT_MODEL","openai/gpt-oss-20b")
    if provider!="groq": raise ValueError("STUDENT_AGENT_PROVIDER must be 'groq'.")
    try: from langchain_groq import ChatGroq
    except ImportError as e: raise RuntimeError("Install langchain-groq to use Groq.") from e
    if not os.getenv("GROQ_API_KEY"): raise RuntimeError("Set GROQ_API_KEY in your environment or .env file.")
    return ChatGroq(model=model,temperature=0)
