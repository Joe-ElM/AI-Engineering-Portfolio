import streamlit as st
import os
import json
from datetime import datetime
from health_agent import HealthAgent
from schemas import UserInput
from config import PERSONALITIES, DEFAULT_OPENAI_SETTINGS, MEDICAL_DISCLAIMER

st.set_page_config(
    page_title="HealthBot - AI Patient Education",
    page_icon="🏥",
    layout="wide"
)

def save_conversation():
    """Save conversation to JSON file"""
    if st.session_state.messages:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"health_conversation_{timestamp}.json"
        
        conversation_data = {
            "timestamp": datetime.now().isoformat(),
            "messages": st.session_state.messages,
            "settings": {
                "personality": st.session_state.get("personality", "friendly"),
                "openai_settings": st.session_state.get("openai_settings", {})
            }
        }
        
        # Save to downloads folder or current directory
        with open(filename, 'w') as f:
            json.dump(conversation_data, f, indent=2)
        
        return filename
    return None

def summarize_conversation():
    """Generate conversation summary"""
    if not st.session_state.messages:
        return "No conversation to summarize."
    
    # Extract key points from conversation
    user_messages = [msg["content"] for msg in st.session_state.messages if msg["role"] == "user"]
    assistant_messages = [msg["content"] for msg in st.session_state.messages if msg["role"] == "assistant"]
    
    summary = f"""
**Conversation Summary**
- **Date**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
- **Topics Discussed**: {len(user_messages)} health questions
- **Key Symptoms/Questions**: {'; '.join(user_messages[:3])}...
- **Total Messages**: {len(st.session_state.messages)}
"""
    return summary

def load_conversation():
    """Load conversation from uploaded file"""
    uploaded_file = st.file_uploader("Upload conversation file", type="json")
    if uploaded_file:
        try:
            conversation_data = json.load(uploaded_file)
            st.session_state.messages = conversation_data.get("messages", [])
            if "settings" in conversation_data:
                settings = conversation_data["settings"]
                st.session_state.personality = settings.get("personality", "friendly")
                st.session_state.openai_settings = settings.get("openai_settings", {})
            st.success("Conversation loaded successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error loading conversation: {str(e)}")

def main():
    st.title("🏥 HealthBot - AI-Powered Patient Education")
    st.markdown("*Educational health information and symptom awareness*")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    
    # Sidebar settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Personality
        personality = st.selectbox(
            "Agent Personality:",
            options=list(PERSONALITIES.keys()),
            format_func=str.title,
            key="personality_select"
        )
        
        # OpenAI parameters
        st.subheader("AI Parameters")
        temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
        top_p = st.slider("Top-p", 0.0, 1.0, 0.9, 0.1)
        max_tokens = st.slider("Max tokens", 100, 2000, 1000, 100)
        
        openai_settings = {
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        }
        
        st.session_state.openai_settings = openai_settings
        st.session_state.personality = personality
        
        # Conversation management
        st.subheader("💾 Conversation")
        
        if st.button("💾 Save"):
            filename = save_conversation()
            if filename:
                st.success(f"Saved: {filename}")
            else:
                st.warning("No conversation to save")
        
        # Clear conversation
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()
    
    # Initialize agent with current settings
    if st.session_state.agent is None:
        st.session_state.agent = HealthAgent(openai_settings)
    else:
        st.session_state.agent.openai_settings = openai_settings
    
    # Medical disclaimer
    with st.expander("⚠️ Important Medical Disclaimer", expanded=False):
        st.error(MEDICAL_DISCLAIMER)
    
    # Main chat interface
    st.subheader("💬 Health Consultation")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            # Show research sources for assistant messages
            if message["role"] == "assistant" and "research_sources" in message:
                with st.expander("📚 Research Sources"):
                    st.write(message["research_sources"])
    
    # Chat input at bottom
    if prompt := st.chat_input("Describe your symptoms, ask about supplements, or any health questions..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Researching health information..."):
                try:
                    # Create user input (simplified - no age/gender for chat)
                    user_input = UserInput(
                        symptoms=prompt,
                        age=None,
                        gender=None
                    )
                    
                    # Process with agent
                    result = st.session_state.agent.process_symptoms(
                        user_input, 
                        personality,
                        thread_id="chat_session"
                    )
                    
                    response = result["response"]
                    research_content = result.get("research_content", "")
                    
                    # Display response
                    st.write(response)
                    
                    # Add assistant message to chat
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response,
                        "research_sources": research_content
                    })
                    
                    # Show research sources
                    if research_content:
                        with st.expander("📚 Research Sources"):
                            st.write(research_content)
                    
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg
                    })
    
    # Usage instructions
    if not st.session_state.messages:
        st.info("""
        👋 **Welcome to HealthBot!** 
        
        Ask me about:
        - Symptoms you're experiencing
        - Vitamins and supplements
        - General health questions
        - When to seek medical care
        
        Type your question in the chat box below to get started.
        """)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OPENAI_API_KEY not found in environment variables")
        st.stop()
    
    if not os.getenv("TAVILY_API_KEY"):
        st.warning("⚠️ TAVILY_API_KEY not found - web search will be limited")
    
    main()