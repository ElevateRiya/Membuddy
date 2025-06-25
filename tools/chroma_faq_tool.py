from langchain_core.tools import tool
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.chains import RetrievalQA
import os
import streamlit as st
# --- NEW: Local LLM imports ---
from langchain.llms import HuggingFacePipeline
from transformers import pipeline
import logging

# --- Pydantic input schema for the tool ---
class FaqVectorInput(BaseModel):
    question: str = Field(description="The user's FAQ question.")

# --- File paths ---
DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'Membuddy_FAQs.csv')
CHROMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'chroma_store')

# --- Module-level cache for embeddings, vector store, and LLM ---
_embeddings = None
_vectordb = None
_retriever = None
_llm = None

# --- Helper: Load or create Chroma vector store (cached) ---
def get_chroma_retriever():
    global _embeddings, _vectordb, _retriever
    if _retriever is not None:
        return _retriever
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    if os.path.exists(CHROMA_PATH) and os.listdir(CHROMA_PATH):
        print("Loading existing Chroma vector store for FAQs...")
        _vectordb = Chroma(persist_directory=CHROMA_PATH, embedding_function=_embeddings)
    else:
        print("Building new Chroma vector store for FAQs from CSV...")
        loader = CSVLoader(DATA_PATH)
        docs = loader.load()
        _vectordb = Chroma.from_documents(docs, _embeddings, persist_directory=CHROMA_PATH)
        _vectordb.persist()
    _retriever = _vectordb.as_retriever(search_kwargs={"k": 2})
    return _retriever

# --- Helper: Load or cache the LLM pipeline ---
def get_llm():
    global _llm
    if _llm is not None:
        return _llm
    hf_pipeline = pipeline(
        "text2text-generation",
        model="google/flan-t5-small"
    )
    _llm = HuggingFacePipeline(pipeline=hf_pipeline)
    return _llm

# --- LangChain tool for semantic FAQ answering ---
@tool(args_schema=FaqVectorInput)
def vector_faq_answer(question: str) -> str:
    """
    Answers FAQs using semantic search over Membuddy_FAQs.csv with Chroma vector store and HuggingFaceEmbeddings.
    Uses a local HuggingFacePipeline LLM (google/flan-t5-small) for answer generation.
    Returns only the answer text (no metadata, no sources).
    """
    try:
        retriever = get_chroma_retriever()
        llm = get_llm()
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=False
        )
        result = qa_chain({"query": question})
        answer = result.get("result") or result.get("answer")
        if not answer:
            return "Sorry, I couldn't find an answer to your question."
        return answer
    except Exception as e:
        st.error(f"FAQ vector tool error: {e}")
        return "Sorry, there was an error answering your question." 