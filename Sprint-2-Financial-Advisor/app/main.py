# import streamlit as st
# import os
# import sys
# import glob
# import json
# import pandas as pd
# from dotenv import load_dotenv

# load_dotenv()

# sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# from tools.finance_tools import plot_price_from_local_data, plot_rolling_average, plot_volatility_histogram
# from rag.rag_tool import search_financial_documents
# from agents.chat_agent import Agent

# @st.cache_resource
# def load_agent():
#     return Agent(
#         name="FinBot",
#         role="Financial Advisor", 
#         instructions="You are a financial advisor. Use tools to help with stock analysis and plotting.",
#         tools=[plot_price_from_local_data, plot_rolling_average, plot_volatility_histogram, search_financial_documents]
#     )

# agent = load_agent()

# st.title("📈 Financial Bot")

# if "messages" not in st.session_state:
#     st.session_state.messages = []
# if "message_plots" not in st.session_state:
#     st.session_state.message_plots = {}

# user_input = st.text_input("Ask about finance:", key="input")

# if st.button("Send") and user_input:
#     st.session_state.messages.append({"role": "user", "content": user_input})
    
#     try:
#         response = agent.invoke(user_input)
#         st.session_state.messages.append({"role": "assistant", "content": response})
        
#         # Track plot for this specific message if one was created
#         if "successfully" in response:
#             plots = glob.glob("data/*.png")
#             if plots:
#                 latest_plot = max(plots, key=os.path.getctime)
#                 message_index = len(st.session_state.messages) - 1
#                 st.session_state.message_plots[message_index] = latest_plot
                
#     except Exception as e:
#         st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
#         st.error(f"Agent error: {str(e)}")

# # Display messages (newest pairs first)
# messages = st.session_state.messages
# i = len(messages) - 1

# while i >= 0:
#     if i > 0 and messages[i]["role"] == "assistant" and messages[i-1]["role"] == "user":
#         # Show user message first
#         with st.chat_message("user"):
#             st.write(messages[i-1]["content"])
        
#         # Show AI response
#         with st.chat_message("assistant"):
#             st.write(messages[i]["content"])
            
#             # Show the specific plot for this message
#             if i in st.session_state.message_plots:
#                 st.image(st.session_state.message_plots[i])
        
#         i -= 2  # Skip both messages
#     else:
#         # Single message (shouldn't happen in normal flow)
#         with st.chat_message(messages[i]["role"]):
#             st.write(messages[i]["content"])
#         i -= 1

# # Conversation Export Feature in Sidebar
# if st.session_state.messages:
#     with st.sidebar:
#         st.subheader("Export Conversation")
        
#         if st.button("JSON"):
#             json_data = json.dumps(st.session_state.messages, indent=2)
#             st.download_button(
#                 label="Download JSON",
#                 data=json_data,
#                 file_name="financial_conversation.json",
#                 mime="application/json",
#                 use_container_width=True
#             )
        
#         if st.button("CSV"):
#             df = pd.DataFrame(st.session_state.messages)
#             csv_data = df.to_csv(index=False)
#             st.download_button(
#                 label="Download CSV",
#                 data=csv_data,
#                 file_name="financial_conversation.csv",
#                 mime="text/csv",
#                 use_container_width=True
#             )


import streamlit as st
import os
import sys
import glob
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from tools.finance_tools import plot_price_from_local_data, plot_rolling_average, plot_volatility_histogram
from rag.rag_tool import search_financial_documents
from agents.chat_agent import Agent

@st.cache_resource
def load_agent():
    return Agent(
        name="FinBot",
        role="Financial Advisor", 
        instructions="You are a financial advisor. Use tools to help with stock analysis and plotting.",
        tools=[plot_price_from_local_data, plot_rolling_average, plot_volatility_histogram, search_financial_documents]
    )

agent = load_agent()

st.title("📈 Financial Bot")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "message_plots" not in st.session_state:
    st.session_state.message_plots = {}

# Form-based input that auto-clears
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("Ask about finance:")
    submitted = st.form_submit_button("Send")

if submitted and user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    try:
        response = agent.invoke(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Track plot for this specific message if one was created
        if "successfully" in response:
            plots = glob.glob("data/*.png")
            if plots:
                latest_plot = max(plots, key=os.path.getctime)
                message_index = len(st.session_state.messages) - 1
                st.session_state.message_plots[message_index] = latest_plot
                
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
        st.error(f"Agent error: {str(e)}")

# Display messages (newest pairs first)
messages = st.session_state.messages
i = len(messages) - 1

while i >= 0:
    if i > 0 and messages[i]["role"] == "assistant" and messages[i-1]["role"] == "user":
        # Show user message first
        with st.chat_message("user"):
            st.write(messages[i-1]["content"])
        
        # Show AI response
        with st.chat_message("assistant"):
            st.write(messages[i]["content"])
            
            # Show the specific plot for this message
            if i in st.session_state.message_plots:
                st.image(st.session_state.message_plots[i])
        
        i -= 2  # Skip both messages
    else:
        # Single message (shouldn't happen in normal flow)
        with st.chat_message(messages[i]["role"]):
            st.write(messages[i]["content"])
        i -= 1

# Conversation Export Feature in Sidebar
if st.session_state.messages:
    with st.sidebar:
        st.subheader("Export Conversation")
        
        if st.button("JSON"):
            json_data = json.dumps(st.session_state.messages, indent=2)
            st.download_button(
                label="Download JSON",
                data=json_data,
                file_name="financial_conversation.json",
                mime="application/json",
                use_container_width=True
            )
        
        if st.button("CSV"):
            df = pd.DataFrame(st.session_state.messages)
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="financial_conversation.csv",
                mime="text/csv",
                use_container_width=True
            )