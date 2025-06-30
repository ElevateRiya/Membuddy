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
    /* Star rating styling */
    .star-rating {
        display: inline-block;
        font-size: 24px;
        cursor: pointer;
        color: #ddd;
        transition: color 0.2s;
    }
    .star-rating:hover,
    .star-rating.active {
        color: #ffd700;
    }
    .star-rating:hover ~ .star-rating {
        color: #ddd;
    }
    .rating-container {
        text-align: center;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Interactive Star Rating Component ---
def create_star_rating():
    """Creates an interactive star rating component."""
    st.markdown("### Please rate your experience:")
    
    # Create columns for the stars
    cols = st.columns(5)
    
    rating = 0
    for i, col in enumerate(cols, 1):
        with col:
            if st.button(f"⭐", key=f"star_{i}", help=f"Rate {i} star{'s' if i > 1 else ''}"):
                rating = i
                st.session_state.rating_selected = i
                st.session_state.show_feedback_form = True
                st.rerun()
    
    return rating

def create_feedback_form():
    """Creates a feedback form after rating is selected."""
    if st.session_state.get('rating_selected'):
        st.markdown(f"**You rated us: {'⭐' * st.session_state.rating_selected}**")
        
        comment = st.text_area("Additional comments (optional):", 
                              placeholder="Tell us more about your experience...",
                              key="feedback_comment")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Submit Feedback", type="primary"):
                try:
                    # Call the collect_feedback tool through the agent
                    feedback_input = f"rating: {st.session_state.rating_selected}"
                    if comment.strip():
                        feedback_input += f", comment: {comment.strip()}"
                    
                    # Use the agent to collect feedback
                    feedback_response = agent.chat(feedback_input)
                    
                    st.success("Thank you for your feedback! Have a great day! 🎉")
                    st.session_state.feedback_submitted = True
                    st.session_state.show_feedback_form = False
                    st.session_state.rating_selected = None
                    
                    # Add the feedback response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": feedback_response})
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error submitting feedback: {e}")
        
        with col2:
            if st.button("Cancel"):
                st.session_state.show_feedback_form = False
                st.session_state.rating_selected = None
                st.rerun()

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
if "show_feedback_form" not in st.session_state:
    st.session_state.show_feedback_form = False
if "rating_selected" not in st.session_state:
    st.session_state.rating_selected = None
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False

# --- Sidebar ---
with st.sidebar:
    st.title("🤖 Membuddy")
    st.info("Your AI Membership Coordinator. How can I help you today?")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.user_email = None
        st.session_state.show_feedback_form = False
        st.session_state.rating_selected = None
        st.session_state.feedback_submitted = False
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

# --- Feedback Form Display ---
if st.session_state.get('show_feedback_form') and not st.session_state.get('feedback_submitted'):
    st.markdown("---")
    create_feedback_form()

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
                
                # Check if the response contains the feedback request
                if "rate your experience" in response.lower() and "★☆☆☆☆" in response:
                    # Show the response without the star rating text
                    response_without_stars = response.split("[★☆☆☆☆]")[0].strip()
                    st.markdown(response_without_stars)
                    
                    # Add the interactive star rating
                    st.markdown("---")
                    create_star_rating()
                    
                    # Store the modified response
                    st.session_state.messages.append({"role": "assistant", "content": response_without_stars})
                else:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
            except Exception as e:
                error_message = f"Sorry, I encountered an error: {e}"
                st.error(error_message, icon="🚨")
                st.session_state.messages.append({"role": "assistant", "content": error_message})
