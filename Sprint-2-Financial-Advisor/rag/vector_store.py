import os
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from rag.document_loader import load_financial_docs

def create_vector_store(persist_directory: str = "data/chroma_db"):
    """Create or load existing ChromaDB vector store"""
    
    # Check if vector store exists
    if os.path.exists(persist_directory):
        print("Loading existing vector store...")
        embeddings = OpenAIEmbeddings()
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
        return vector_store
    
    print("Creating new vector store...")
    
    # Load documents
    documents = load_financial_docs()
    
    if not documents:
        raise ValueError("No documents found to process")
    
    # Create embeddings
    embeddings = OpenAIEmbeddings()
    
    # Create vector store
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    
    print(f"Vector store created with {len(documents)} document chunks")
    return vector_store

def search_documents(query: str, vector_store, k: int = 3):
    """Search for relevant documents"""
    results = vector_store.similarity_search(query, k=k)
    return results