import os
from typing import List, Dict
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

def load_financial_docs(docs_path: str = "data/financial_docs/") -> List[Dict]:
    """Load and split PDF documents from financial_docs folder"""
    
    documents = []
    
    # Get all PDF files
    pdf_files = [f for f in os.listdir(docs_path) if f.endswith('.pdf')]
    
    for pdf_file in pdf_files:
        file_path = os.path.join(docs_path, pdf_file)
        
        # Extract quarter and year from filename
        # Example: FY24_Q1_Consolidated_Financial_Statements.pdf
        parts = pdf_file.replace('.pdf', '').split('_')
        fy_year = parts[0]  # FY24 or FY25
        quarter = parts[1]  # Q1, Q2, etc.
        
        # Convert fiscal year to calendar year
        if fy_year == 'FY24':
            year = '2024'
        elif fy_year == 'FY25':
            year = '2025'
        else:
            year = fy_year.replace('FY', '20')
        
        print(f"Loading {pdf_file}...")
        
        # Load PDF
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        
        # Split into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=500
        )
        
        chunks = text_splitter.split_documents(pages)
        
        # Add metadata with date ranges for 2025 quarters
        if quarter == "Q1" and fy_year == "FY25":
            quarter_dates = "Oct-Dec 2024"
        elif quarter == "Q2" and fy_year == "FY25":
            quarter_dates = "Jan-Mar 2025"
        else:
            quarter_dates = f"{quarter} {year}"
        
        # Add metadata to each chunk
        for chunk in chunks:
            chunk.metadata.update({
                "quarter": quarter,
                "year": year,
                "fiscal_year": fy_year,
                "period": f"{quarter} {year}",
                "quarter_dates": quarter_dates,
                "company": "Apple",
                "document_type": "financial_statement",
                "source_file": pdf_file
            })
            
        documents.extend(chunks)
    
    print(f"Loaded {len(documents)} document chunks")
    return documents