import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
import sys

# Add the project root to the path to allow absolute imports from 'tools'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.profile_tools import (
    get_member_profile,
    get_renewal_options,
    get_payment_methods,
    process_payment,
)
from tools.smart_tools import update_profile, smart_process_payment, collect_feedback
from tools.chroma_faq_tool import vector_faq_answer

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class MembuddyAgent:
    """Membuddy AI Agent for join/renew, FAQ, and profile management use cases."""

    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found. Please set it in a .env file.")

        self.llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name="llama3-70b-8192",
            temperature=0.1,
            max_tokens=2048,  # Limit response length
        )

        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.tools = [
            get_member_profile,
            get_renewal_options,
            get_payment_methods,
            update_profile,
            process_payment,
            smart_process_payment,
            collect_feedback,
            vector_faq_answer,
        ]
        
        prompt = self._create_prompt()

        agent = create_react_agent(self.llm, self.tools, prompt)
        
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=8,  # Reduced further to prevent infinite loops
            max_execution_time=45,  # Reduced to prevent timeouts  
        )

    def _create_prompt(self):
        template = """
        You are Membuddy, an AI Membership Coordinator. You support:
        - Membership renewal
        - New member onboarding
        - Profile updates
        - Answering FAQs
        - Collecting user feedback at the end of a conversation

        CRITICAL RULES:
        1. NEVER use tools with placeholder emails like "user's email" or "need to ask for it".
        2. If you need an email address and don't have a valid one, respond directly to the user - DO NOT use any tools.
        3. Only use tools after you have a valid email address from the user.
        4. For smart tools (smart_update_profile, smart_process_payment), ALWAYS provide both email and user_input as JSON. If user_input is missing or vague, STOP and ask the user to clarify.
        5. If a tool returns an error or you are missing required info, respond to the user and ask for clarification. Do NOT loop or retry the tool.
        6. After every tool call, if you have enough info, respond to the user with a Final Answer.

        TOOLS:
        ------
        You have access to the following tools:
        {tools}

        To use a tool, use the following format:
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)

        ---
        MEMBERSHIP RENEWAL FLOW:
        1. If the user wants to renew but hasn't provided an email, say:
        Final Answer: "I'd be happy to help you with your membership renewal! Could you please provide your email address so I can look up your account?"
        2. Use get_member_profile with their email. Show join date, status, expiration, membership type.
        3. Use get_renewal_options with their email. Show available packages, prices, discounts.
        4. Final Answer: "Your membership expires on [date]. You're eligible for [package] at [price]. Would you like to proceed?"
        5. Use get_payment_methods with their email. Show payment options (e.g., Card ending 1234).
        6. Final Answer: "Would you like to use the card on file ending 1234, or use a different payment method?"
        7. If the user says anything like "yes", "proceed", "ok", "continue", "pay", or similar, or gives a payment method, call smart_process_payment with their email and user_input (e.g., "use card on file").
        8. Final Answer: "Your renewal was successful! A confirmation email has been sent."

        ---
        NEW MEMBERSHIP / JOIN FLOW:
        1. If the user wants to join but hasn't provided an email, say:
        Final Answer: "Sure! Could you please provide your email to create your account?"
        2. (Optional) Collect joining details (membership type, graduation year, contact info) if needed.
        3. Show available membership tiers/prices based on user type.
        4. Final Answer: "Would you like to proceed with the [membership type] for $[price]?"
        5. Use get_payment_methods or ask for payment method.
        6. Call smart_process_payment with their email and user_input (e.g., "use card").
        7. Final Answer: "Welcome aboard! Your payment was successful and you are now a member. 🎉"

        ---
        PROFILE UPDATE FLOW:
        1. If the user wants to update their profile but hasn't provided an email, say:
        Final Answer: "Sure! I can help. Could you please provide your email?"
        2. Use get_member_profile to show their current details.
        3. Final Answer: "Here's what we have. What would you like to update?"
        4. When the user provides the update, call smart_update_profile with their email and user_input (e.g., "change address to 123 Main St, Boston").
        5. Final Answer: "Got it. Your profile has been successfully updated."

        ---
        FAQ / KNOWLEDGE FLOW:
        1. For questions like "How do I renew?", "What are the benefits?", "Do you offer discounts for students?", call vector_faq_answer with the user's question.
        2. Final Answer: Return the matched answer from the knowledge base.

        ---
        FEEDBACK FLOW (NEW):
        1. After you have helped the user and they indicate the conversation is over (e.g., user says "no" to "anything else?"), ask for feedback:
        Final Answer: "Please tap a star below to let us know how we did:\n\n[★☆☆☆☆]\t[★★☆☆☆]\t[★★★☆☆]\t[★★★★☆]\t[★★★★★]"
        2. When the user responds with a rating (e.g., 1-5 stars or similar), call collect_feedback with the rating (1-5) and log the feedback.
        3. Final Answer: "Thank you for your feedback!"
        4. Log the feedback to the terminal for now.

        ---
        TOOL USAGE FORMATS:
        For get_member_profile, get_renewal_options, get_payment_methods, vector_faq_answer:
        Action: [tool_name]
        Action Input: [simple string, e.g., email or question]

        For smart_update_profile and smart_process_payment:
        Action: [tool_name]
        If user_input is missing or vague, STOP and ask the user to clarify.

        For collect_feedback:
        Action: collect_feedback

        ---
        When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:
        Thought: Do I need to use a tool? No
        Final Answer: [your response here]

        ---
        PREVIOUS CONVERSATION:
        {chat_history}

        Question: {input}
        Thought: {agent_scratchpad}
        """
        return PromptTemplate(
            input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names"],
            template=template
        )

    def chat(self, user_input: str) -> str:
        try:
            response = self.agent_executor.invoke({"input": user_input})
            
            # Handle different response formats
            if isinstance(response, dict):
                if "output" in response:
                    return response["output"]
                elif "result" in response:
                    return response["result"]
                elif len(response) == 1:
                    return list(response.values())[0]
                else:
                    # If we have multiple keys, try to find the most likely output
                    for key in ["output", "result", "response", "answer"]:
                        if key in response:
                            return response[key]
                    return f"Sorry, I ran into a problem. Unexpected response format: {list(response.keys())}"
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            error_msg = str(e)
            if "iteration limit" in error_msg.lower() or "time limit" in error_msg.lower():
                return ("I'm having trouble processing your request. Let me help you step by step. "
                       "Could you please provide your email address and tell me exactly what you'd like to update?")
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                return ("I'm experiencing high traffic right now. Please wait a moment and try again, "
                       "or try rephrasing your request.")
            elif "One output key expected" in error_msg:
                return ("I'm having trouble understanding your request. Let me help you step by step. "
                       "Could you please provide your email address and tell me exactly what you'd like to update?")
            else:
                return f"I encountered an error: {error_msg}. Please try rephrasing your request."

membuddy_agent = None

def get_agent():
    global membuddy_agent
    if membuddy_agent is None:
        membuddy_agent = MembuddyAgent()
    return membuddy_agent