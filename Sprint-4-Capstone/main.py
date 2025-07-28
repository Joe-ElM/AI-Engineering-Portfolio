import streamlit as st
import os
import time
from datetime import datetime
from multi_agent_health_system import MultiAgentHealthSystem
from extended_schemas import UserInput, PatientContext
from config import PERSONALITIES,  MEDICAL_DISCLAIMER 

st.set_page_config(
    page_title="HealthBot - AI Patient Education",
    page_icon="🏥",
    layout="wide"
)


def main():
    st.title("🏥 HealthBot - Multi-Agent AI Health System")
    st.markdown("*Advanced multi-agent health education and symptom analysis*")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "agent_session_id" not in st.session_state:
        # Create a unique session ID for this chat session
        st.session_state.agent_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
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
        
        # Multi-Agent Status
        st.subheader("🤖 Multi-Agent System")
        st.info("""
        **Active Agents:**
        - 🔄 Context Resolver
        - 🚨 Triage Agent
        - 🔍 Diagnosis Agent  
        - 🥗 Diet Agent
        - 💊 Treatment Agent
        - 🧠 Synthesis Agent
        - 📝 Coherence Checker
        - 🔍 Validation Agent
        """)
        
        # Patient Summary
        st.subheader("👤 Patient Profile")
        if st.session_state.agent and st.session_state.agent.patient_context:
            ctx = st.session_state.agent.patient_context
            if ctx.conditions or ctx.lab_values or ctx.symptoms_timeline:
                st.success("✅ Active Profile")
                with st.expander("View Summary", expanded=False):
                    st.markdown(st.session_state.agent.get_patient_summary())
            else:
                st.info("📋 Building profile...")
        else:
            st.info("📋 No profile yet")
        
        # Session management
        st.subheader("💭 Session")
        
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.session_state.agent = None  # Reset agent to clear conversation history
            st.session_state.agent_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.rerun()
    
    # Initialize multi-agent system - maintain same instance for conversation continuity
    if st.session_state.agent is None:
        st.session_state.agent = MultiAgentHealthSystem(openai_settings)
    else:
        # Update settings without resetting the agent
        st.session_state.agent.openai_settings = openai_settings
        st.session_state.agent.llm.temperature = openai_settings["temperature"]
        st.session_state.agent.llm.top_p = openai_settings["top_p"]
        st.session_state.agent.llm.max_tokens = openai_settings["max_tokens"]
    
    # Medical disclaimer
    with st.expander("⚠️ Important Medical Disclaimer", expanded=False):
        st.error(MEDICAL_DISCLAIMER)
    
    # Main chat interface
    st.subheader("💬 Multi-Agent Health Consultation")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            # Show agent details for assistant messages
            if message["role"] == "assistant" and "agent_details" in message:
                with st.expander("🤖 Agent Processing Details"):
                    details = message["agent_details"]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Triage Result:**")
                        st.json(details.get("triage_result", {}))
                        
                        st.write("**Diet Recommendations:**")
                        st.json(details.get("diet_result", {}))
                    
                    with col2:
                        st.write("**Diagnosis Analysis:**")
                        st.json(details.get("diagnosis_result", {}))
                        
                        st.write("**Treatment Plan:**")
                        st.json(details.get("treatment_result", {}))
                    
                    st.write("**Validation Status:**", details.get("validation_status", "Unknown"))
    
    # Chat input
    if prompt := st.chat_input("Describe your symptoms or health questions..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Process with multi-agent system
        with st.chat_message("assistant"):
            try:
                # Create user input
                user_input = UserInput(
                    symptoms=prompt,
                    age=None,
                    gender=None
                )
                
                # Check if this is likely a follow-up question (short and contains pronouns)
                is_followup = len(prompt.split()) < 10 and any(word in prompt.lower() for word in ["it", "this", "that", "these", "those", "them"])
                
                if is_followup:
                    # Process follow-ups without progress bar
                    with st.spinner("Processing..."):
                        result = st.session_state.agent.process_health_query(
                            user_input, 
                            personality,
                            thread_id=st.session_state.agent_session_id
                        )
                else:
                    # Use progress bar only for initial complex queries
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def update_progress(status, progress):
                        status_text.text(status)
                        progress_bar.progress(progress)
                    
                    result = st.session_state.agent.process_health_query(
                        user_input, 
                        personality,
                        thread_id=st.session_state.agent_session_id,
                        progress_callback=update_progress
                    )
                    
                    progress_bar.empty()
                    status_text.empty()
                
                response = result["response"]
                
                # Stream the response character by character
                response_placeholder = st.empty()
                displayed_text = ""
                
                # Display response with streaming effect
                for char in response:
                    displayed_text += char
                    response_placeholder.markdown(displayed_text)
                    time.sleep(0.005)  # Adjust speed as needed
                
                # Add assistant message with agent details
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response,
                    "agent_details": {
                        "triage_result": result["triage_result"].dict(),
                        "diagnosis_result": result["diagnosis_result"].dict(),
                        "diet_result": result["diet_result"].dict(),
                        "treatment_result": result["treatment_result"].dict(),
                        "validation_status": result["validation_status"]
                    }
                })
                
                # Show processing pipeline
                with st.expander("🔄 Agent Processing Pipeline"):
                    st.write("✅ Context Resolver - References resolved")
                    st.write("✅ Triage Agent - Classification complete")
                    st.write("✅ Diagnosis Agent - Research and analysis complete")
                    st.write("✅ Diet Agent - Nutritional recommendations complete")
                    st.write("✅ Treatment Agent - Care guidance complete")
                    st.write("✅ Synthesis Agent - Plan integration complete")
                    st.write(f"✅ Validation Agent - Status: {result['validation_status']}")
                
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
        👋 **Welcome to the Multi-Agent HealthBot!** 
        
        This advanced system uses 8 specialized AI agents with **persistent memory**:
        - **Context Resolver**: Understands references and tracks your health journey
        - **Triage Agent**: Smart routing - only uses relevant agents for faster responses
        - **Diagnosis Agent**: Researches symptoms with awareness of your conditions
        - **Diet Agent**: Personalized nutrition based on your progress
        - **Treatment Agent**: Tracks what's working and suggests next steps
        - **Synthesis Agent**: Creates coherent responses that build on past conversations
        - **Coherence Checker**: Ensures continuity and avoids repetition
        - **Validation Agent**: Ensures accuracy and safety
        
        Start by describing your symptoms or health questions!
        """)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OPENAI_API_KEY not found in environment variables")
        st.stop()
    
    if not os.getenv("TAVILY_API_KEY"):
        st.warning("⚠️ TAVILY_API_KEY not found - web search will be limited")
    
    main()