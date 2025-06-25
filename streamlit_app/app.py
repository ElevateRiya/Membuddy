import streamlit as st
import sys
import os
import re

# Add the project root to the path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_agent.agent import get_agent

# --- Page Configuration ---
st.set_page_config(
    page_title="Membuddy",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="auto",
)

# --- Styling ---
st.markdown("""
<style>
    /* General body styling */
    body {
        background-color: #F0F2F6;
    }
    /* Main chat container */
    .st-emotion-cache-1jicfl2 {
        padding-top: 2rem;
    }
    /* Chat messages */
    .stChatMessage {
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    /* User message */
    [data-testid="chat-message-container"]:has([data-testid="chat-avatar-user"]) {
        background-color: #DCF8C6;
    }
    /* Assistant message */
    [data-testid="chat-message-container"]:has([data-testid="chat-avatar-assistant"]) {
        background-color: #FFFFFF;
    }
    /* Hide Streamlit footer */
    .st-emotion-cache-h5rgaw {
        display: none;
    }
</style>
""", unsafe_allow_html=True)


# --- Agent Initialization ---
@st.cache_resource
def initialize_agent():
    """Initializes the Membuddy agent."""
    try:
        return get_agent()
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}", icon="🚨")
        st.stop()

agent = initialize_agent()

# --- Session State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# --- Sidebar ---
with st.sidebar:
    st.title("🤖 Membuddy")
    st.info("Your AI Membership Coordinator. How can I help you today?")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.user_email = None
        st.rerun()
    st.markdown("---")
    st.markdown("**Example Questions:**")
    st.markdown("- I want to renew my membership.")
    st.markdown("- What are the benefits for student members?")
    st.markdown("- How do I renew?")
    st.markdown("- I want to update my profile.")
    st.markdown("- Update my graduation year to 2023.")
    st.markdown("- Change my address.")

# --- Main Chat Interface ---
st.title("Membuddy Chat")

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input and Response ---
if prompt := st.chat_input("Ask Membuddy anything about renewals or FAQs..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Extract email if present
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', prompt)
    if email_match:
        st.session_state.user_email = email_match.group(0)
        st.toast(f"Thanks! I've noted your email: {st.session_state.user_email}", icon="📧")

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Membuddy is thinking..."):
            try:
                # If we have a user email, include it in the context for the agent
                if st.session_state.user_email:
                    enhanced_prompt = f"User email: {st.session_state.user_email}\n\nUser message: {prompt}"
                else:
                    enhanced_prompt = prompt
                
                response = agent.chat(enhanced_prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_message = f"Sorry, I encountered an error: {e}"
                st.error(error_message, icon="🚨")
                st.session_state.messages.append({"role": "assistant", "content": error_message})
