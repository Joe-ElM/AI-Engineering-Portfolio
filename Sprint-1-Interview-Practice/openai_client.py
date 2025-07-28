# import os
import streamlit as st
from   openai import OpenAI


# Load API key from local file
# with open('D:\\Visual Studio Code\\desktop_openai.txt', 'r') as f:
#     os.environ['OPENAI_API_KEY'] = f.read().strip()

# Access the key from environment
# api_key = os.getenv("OPENAI_API_KEY")

# Load API key from Streamlit secrets (for deployment)
api_key = st.secrets["OPENAI_API_KEY"]

# Create AOpenAI cleint using loaded key
# api_key = os.getenv("OPENAI_API_KEY")
client  = OpenAI(api_key= api_key)



# Chat copmpletion wrapper
def get_completion(messages, 
                   model       = "gpt-4o-mini", 
                   temperature = 0.5, 
                   max_tokens  = 200):
    """
    Call the OpenAI Chat API with the given messages and parameters.
    """
    response = client.chat.completions.create(
                                            model       = model,
                                            messages    = messages,
                                            temperature = temperature,
                                            max_tokens  = max_tokens)
    
    return response.choices[0].message.content