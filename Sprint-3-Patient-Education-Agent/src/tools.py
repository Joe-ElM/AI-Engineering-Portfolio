import os
try:
    from langchain_community.tools.tavily_search import TavilySearchResults
except ImportError:
    TavilySearchResults = None
from langchain_community.document_loaders import WikipediaLoader
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from config import TAVILY_API_KEY

class SearchQuery(BaseModel):
    search_query: str = Field(description="Search query for retrieval")

def search_wikipedia(symptoms: str, max_docs: int = 2) -> str:
    """Search Wikipedia for medical information about symptoms"""
    try:
        # Create search query
        search_query = f"{symptoms} medical symptoms causes treatment"
        
        # Search Wikipedia
        loader = WikipediaLoader(query=search_query, load_max_docs=max_docs)
        docs = loader.load()
        
        # Format results
        formatted_docs = "\n\n---\n\n".join([
            f'<Document source="{doc.metadata["source"]}" page="{doc.metadata.get("page", "")}"/>\n{doc.page_content}\n</Document>'
            for doc in docs
        ])
        
        return formatted_docs
        
    except Exception as e:
        return f"Error searching Wikipedia: {str(e)}"

def search_tavily(symptoms: str, max_results: int = 3) -> str:
    """Search web using Tavily for current medical information"""
    try:
        # Initialize Tavily search
        tavily_search = TavilySearchResults(
            max_results=max_results,
            api_key=TAVILY_API_KEY
        )
        
        # Create medical-focused search query
        search_query = f"{symptoms} symptoms medical information causes treatment"
        
        # Search
        search_docs = tavily_search.invoke(search_query)
        
        # Format results
        formatted_docs = "\n\n---\n\n".join([
            f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
            for doc in search_docs
        ])
        
        return formatted_docs
        
    except Exception as e:
        return f"Error searching Tavily: {str(e)}"

def generate_search_query(symptoms: str, llm: ChatOpenAI) -> str:
    """Generate optimized search query from user symptoms"""
    try:
        search_instructions = SystemMessage(content="""
        You are tasked with creating an optimized medical search query.
        
        Convert the user's symptom description into a well-structured medical search query
        that will find relevant, reliable medical information.
        
        Focus on:
        - Medical terminology
        - Symptom combinations
        - Potential conditions
        - Treatment information
        
        Keep the query concise but comprehensive.
        """)
        
        structured_llm = llm.with_structured_output(SearchQuery)
        result = structured_llm.invoke([search_instructions] + [f"Symptoms: {symptoms}"])
        
        return result.search_query
        
    except Exception as e:
        return symptoms  # Fallback to original symptoms

def combine_search_results(wikipedia_results: str, tavily_results: str) -> str:
    """Combine and format search results from multiple sources"""
    combined = []
    
    if wikipedia_results and "Error" not in wikipedia_results:
        combined.append("## Wikipedia Sources:\n" + wikipedia_results)
    
    if tavily_results and "Error" not in tavily_results:
        combined.append("## Web Sources:\n" + tavily_results)
    
    if not combined:
        return "No reliable medical information found. Please consult a healthcare professional."
    
    return "\n\n".join(combined)
