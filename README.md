# 🤖 Membuddy - AI Membership Coordinator

Membuddy is an intelligent AI agent designed to help with membership management operations. It provides a conversational interface for handling membership renewals, new member onboarding, profile updates, and answering frequently asked questions.

## 🚀 Key Features

- **Membership Renewal**: Guide members through renewal processes with personalized options
- **New Member Onboarding**: Help new members join with appropriate membership tiers
- **Profile Management**: Update member information like email, address, and graduation year
- **Payment Processing**: Handle payments using stored payment methods
- **FAQ Support**: Semantic search for membership questions using AI-powered vector search
- **Smart Input Processing**: Understand natural language requests and correct typos
- **Modern Web Interface**: Beautiful Streamlit-based chat interface

## 📁 Project Structure

```
Membuddy/
├── data/
│   ├── AI Agent Data.xlsx          # Member data (Master Table, Payment Table)
│   └── Membuddy_FAQs.csv          # FAQ database for semantic search
├── chroma_store/                   # Vector database for FAQ search
├── streamlit_app/
│   └── app.py                      # Main Streamlit chat interface
├── tools/
│   ├── profile_tools.py            # Core membership tools (profiles, renewals, payments)
│   ├── smart_tools.py              # Smart input processing and feedback collection
│   └── chroma_faq_tool.py         # FAQ semantic search tool
├── langchain_agent/
│   └── agent.py                    # AI agent logic and initialization
└── requirements.txt                # Python dependencies
```

## 🛠️ Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Get your free API key from [Groq Console](https://console.groq.com/).

### 3. Prepare Your Data

Ensure your `AI Agent Data.xlsx` file is in the `data/` directory with these sheets:

**Master Table** (required):
- Member ID, Full Name, Email, Address, Join Date, Membership Type, Graduation Year, Expiration Date

**Payment Table** (required):
- Member ID, Payment Method, Last Payment Amount

Also place `Membuddy_FAQs.csv` in the `data/` directory for FAQ functionality.

## 🚀 Running Membuddy

### Start the Chat Interface

```bash
cd streamlit_app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 💬 How to Use Membuddy

### Membership Renewal
```
User: "I want to renew my membership"
Membuddy: "I'd be happy to help! Could you please provide your email address?"
User: "john.doe@example.com"
Membuddy: [Shows membership details and renewal options]
```

### New Member Onboarding
```
User: "I want to join as a new member"
Membuddy: "Welcome! Could you please provide your email to create your account?"
User: "newmember@example.com"
Membuddy: [Shows available membership tiers and pricing]
```

### Profile Updates
```
User: "Update my graduation year to 2023"
Membuddy: "I'll update your graduation year to 2023. Since you're graduating in 2023 
         and currently a Student member, you're eligible for the Pharmacist 
         Transition Package ($100, Early Bird $90 before June 15)."
```

### FAQ Questions
```
User: "How do I renew my membership?"
Membuddy: [Provides detailed answer from FAQ database]

User: "What are the benefits for student members?"
Membuddy: [Searches and returns relevant information]
```

### Payment Processing
```
User: "Use my card to pay $100"
Membuddy: "I'll process a payment of $100 using your Card ending 1234. 
         Payment completed successfully!"
```

## 🧠 Smart Features

### Natural Language Processing
- **Typo Correction**: "membreshi" → "membership", "updte" → "update"
- **Smart Field Extraction**: Understands "update graduation year to 2023"
- **Payment Method Detection**: Recognizes "use my card", "pay with ACH"
- **Amount Extraction**: Understands "$100", "50 dollars", "75 bucks"

### Context Awareness
- Remembers user email throughout conversation
- Tracks conversation state and previous actions
- Provides personalized responses based on member data

### Intelligent Validation
- Email format validation
- Graduation year range checking (1900-2030)
- Address completeness validation
- Helpful error messages with suggestions

## 🔧 Configuration

### Groq Models

You can change the AI model in `langchain_agent/agent.py`:

```python
self.llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama3-70b-8192",  # Change this
    temperature=0.1
)
```

Available models:
- `llama3-8b-8192` (fast, cost-effective)
- `llama3-70b-8192` (more capable, default)
- `mixtral-8x7b-32768` (balanced)
- `gemma2-9b-it` (Google's model)

### FAQ Vector Store

The FAQ system uses:
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
- **Vector Store**: Chroma with local persistence
- **Local LLM**: `google/flan-t5-small` for answer generation

## 📊 Data Requirements

### Master Table Format
| Column | Type | Description |
|--------|------|-------------|
| Member ID | Integer | Unique identifier |
| Full Name | String | Member's full name |
| Email | String | Member's email address |
| Address | String | Member's address |
| Join Date | Date | Membership start date |
| Membership Type | String | Student, Pharmacist, etc. |
| Graduation Year | Integer | Year of graduation (for students) |
| Expiration Date | Date | When membership expires |

### Payment Table Format
| Column | Type | Description |
|--------|------|-------------|
| Member ID (PK) | Integer | Reference to member |
| Payment Method | String | Card ending 1234, ACH, etc. |
| Last Payment Amount | Float | Amount of last payment |

### FAQ CSV Format
| Column | Type | Description |
|--------|------|-------------|
| Question | String | FAQ question |
| Answer | String | Detailed answer |

## 🐛 Troubleshooting

### Common Issues

1. **API Key Error**: Ensure `GROQ_API_KEY` is set in `.env`
2. **Data Loading Error**: Check if `AI Agent Data.xlsx` exists in `data/` directory
3. **Import Errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`
4. **Memory Issues**: Clear chat history using the sidebar button

### Windows Compatibility

If you encounter import errors on Windows:
```bash
pip install --upgrade langchain-community
pip install --upgrade chromadb
```

### Debug Mode

Enable verbose logging in `langchain_agent/agent.py`:
```python
self.agent_executor = AgentExecutor(
    agent=agent,
    tools=self.tools,
    memory=self.memory,
    verbose=True,  # Change to True for debugging
    handle_parsing_errors=True,
    max_iterations=20,
    max_execution_time=180,
)
```

## 🧪 Testing

Test individual tools:

```python
# Test profile management
from tools.profile_tools import get_member_profile
result = get_member_profile.invoke({"email": "john.doe@example.com"})
print(result)

# Test FAQ system
from tools.chroma_faq_tool import vector_faq_answer
result = vector_faq_answer.invoke({"question": "How do I renew?"})
print(result)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the tool documentation in the `tools/` directory
3. Open an issue on GitHub

---

**Membuddy** - Your intelligent membership management assistant! 🤖

*Built with LangChain, Groq LLM, Streamlit, and Chroma Vector Store* 