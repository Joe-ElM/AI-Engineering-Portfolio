import os
from langchain.tools import tool
from rag.vector_store import create_vector_store, search_documents

# Initialize vector store globally
try:
    vector_store = create_vector_store()
except Exception as e:
    print(f"Warning: Could not initialize vector store: {e}")
    vector_store = None

@tool
def search_financial_documents(query: str, max_results: int = 10):
    """
    Search Apple's financial documents for specific information.
    
    Use this when user asks about:
    - Financial metrics (revenue, income, EPS, earnings, profit)
    - Operating expenses, R&D, research and development
    - Quarter comparisons (Q1 vs Q2)
    - Year-over-year analysis
    - Balance sheet items
    - Cash flow information
    
    Args:
        query (str): Search query for financial information
        max_results (int): Maximum number of results to return
    
    Returns:
        str: Relevant financial information from documents
    """
    
    if not vector_store:
        return "Financial documents not available. Vector store not initialized."
    
    try:
        # Search for relevant documents
        results = search_documents(query, vector_store, k=max_results)
        
        if not results:
            return f"No relevant financial information found for: {query}"
        
        # Format results
        response = f"Financial information for '{query}':\n\n"
        
        for i, doc in enumerate(results, 1):
            metadata = doc.metadata
            quarter = metadata.get('quarter', 'Unknown')
            year = metadata.get('year', 'Unknown')
            
            response += f"**{quarter} {year}:**\n"
            response += f"{doc.page_content[:500]}...\n\n"
        
        return response
        
    except Exception as e:
        return f"Error searching financial documents: {str(e)}"