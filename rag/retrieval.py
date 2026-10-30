"""Persistent FAISS policy index backed by local sentence-transformer embeddings."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
import re

from langchain_core.documents import Document

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

class PolicyRetriever:
    """Build or load a local FAISS index and return relevant cited sections.

    Sections are chunks for the concise handbook. Normalized vectors let us
    map squared L2 distance to cosine similarity as 1 - distance / 2.
    """
    def __init__(self, path="rag/sample_handbook.md", threshold=0.20, index_dir=None, embedding_model=None):
        try:
            from langchain_community.vectorstores import FAISS
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError as exc:
            raise RuntimeError("Install langchain-community, langchain-huggingface, faiss-cpu, and sentence-transformers from requirements.txt.") from exc
        self.path=Path(path); self.threshold=float(threshold)
        self.embedding_model=embedding_model or os.getenv("STUDENT_AGENT_EMBEDDING_MODEL",DEFAULT_EMBEDDING_MODEL)
        self.index_dir=Path(index_dir or os.getenv("STUDENT_AGENT_INDEX_DIR","rag/index"))
        content=self.path.read_text(encoding="utf-8")
        self.fingerprint=hashlib.sha256((self.embedding_model+"\0"+content).encode("utf-8")).hexdigest()
        self.embeddings=HuggingFaceEmbeddings(model_name=self.embedding_model,model_kwargs={"device":"cpu"},encode_kwargs={"normalize_embeddings":True})
        manifest=self.index_dir/"manifest.json"
        if manifest.exists() and (self.index_dir/"index.faiss").exists() and json.loads(manifest.read_text(encoding="utf-8")).get("fingerprint")==self.fingerprint:
            # The FAISS index and pickle are created and managed by this app.
            self.store=FAISS.load_local(str(self.index_dir),self.embeddings,allow_dangerous_deserialization=True)
        else:
            sections=re.split(r"(?=^## )",content,flags=re.M)
            chunks=[s.strip() for s in sections if s.strip() and not s.lstrip().startswith("# Illustrative")]
            if not chunks: raise ValueError(f"No policy sections found in {self.path}.")
            docs=[Document(page_content=text,metadata={"chunk_id":f"handbook-{i:02d}","source":self.path.name}) for i,text in enumerate(chunks)]
            self.store=FAISS.from_documents(docs,self.embeddings,normalize_L2=True)
            self.index_dir.mkdir(parents=True,exist_ok=True); self.store.save_local(str(self.index_dir))
            manifest.write_text(json.dumps({"fingerprint":self.fingerprint,"embedding_model":self.embedding_model,"source":str(self.path)},indent=2),encoding="utf-8")

    def retrieve(self, query, top_k=2):
        results=[]
        for doc,distance in self.store.similarity_search_with_score(query,k=top_k):
            score=max(-1.0,min(1.0,1.0-float(distance)/2.0))
            if score>=self.threshold:
                results.append({"chunk_id":doc.metadata["chunk_id"],"source":doc.metadata["source"],"text":doc.page_content,"score":score})
        return results
