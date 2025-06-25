# 🤖 Membuddy - AI Membership Coordinator

Membuddy is an intelligent AI agent designed to assist with membership management operations including onboarding, engagement, renewals, support, profile management, and insights.

## 🚀 Features

- **Member Information Management**: Fetch and update member profiles
- **Member Profile Management**: Complete profile update workflow with validation
- **Renewal Assistance**: Guide members through renewal processes
- **Payment Integration**: Initiate payment workflows (mock implementation)
- **Feedback Collection**: Collect and store member feedback
- **FAQ Support**: Semantic search for membership questions
- **Multi-sheet Data Support**: Works with complex Excel data structures
- **Conversational AI**: Natural language interaction using Groq LLM
- **Modern Web Interface**: Beautiful Streamlit-based chat interface

## 📁 Project Structure

```
membuddy/
├── data/
│   ├── AI Agent Data.xlsx          # Member data (multiple sheets)
│   └── Membuddy_FAQs.csv          # FAQ database for semantic search
├── chroma_store/                   # Vector database for FAQ search
├── streamlit_app/
│   └── app.py                      # Main Streamlit chat interface
├── tools/
│   ├── profile_tools.py            # LangChain-compatible tools
│   └── chroma_faq_tool.py         # FAQ semantic search tool
├── langchain_agent/
│   └── agent.py                    # Agent logic and initialization
└── requirements.txt                # Python dependencies
```

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Data Preparation

Ensure your `AI Agent Data.xlsx` file is in the `data/` directory with the following sheets:
- **Master Table**: Main member information (required)
- **Payment Table**: Payment records (required)
- **Feedback Table**: Member feedback (optional)

Also ensure `Membuddy_FAQs.csv` is in the `data/` directory for FAQ functionality.

## 🚀 Running the Application

### Streamlit App (Recommended)

```bash
cd streamlit_app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 💬 Usage Examples

### Member Profile Management
- "I want to update my profile"
- "Update my graduation year to 2023"
- "Change my address to 123 Main St"
- "Update my email to new@example.com"

### Member Information
- "Get information for member 123456"
- "What are my membership benefits?"
- "When does my membership expire?"

### Renewals and Payments
- "I want to renew my membership"
- "What are the renewal options?"
- "Initiate payment for $200"

### FAQ Support
- "How do I renew my membership?"
- "What are the benefits for student members?"
- "How do I update my profile?"

### Feedback
- "Give feedback: 5 stars"
- "Rate my experience: 4 stars"

## 🔧 Configuration

### Groq Models

You can change the Groq model in `langchain_agent/agent.py`:

```python
self.llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama3-8b-8192",  # Change this
    temperature=0.1
)
```

Available models:
- `llama3-8b-8192` (fast, cost-effective)
- `llama3-70b-8192` (more capable)
- `mixtral-8x7b-32768` (balanced)
- `gemma2-9b-it` (Google's model)

## 🧪 Testing

Test individual tools:

```python
# Test profile management
from tools.profile_tools import get_member_profile, update_member_profile
result = get_member_profile.invoke({"email": "sarah.jones@email.com"})
print(result)
```

## 🔍 Troubleshooting

### Common Issues

1. **API Key Error**: Ensure `GROQ_API_KEY` is set in `.env`
2. **Data Loading Error**: Check if `AI Agent Data.xlsx` exists in `data/` directory
3. **Import Errors**: Make sure all dependencies are installed
4. **Memory Issues**: Clear chat history using the sidebar button

### Debug Mode

Enable verbose logging in `langchain_agent/agent.py`:

```python
self.agent_executor = AgentExecutor(
    agent=agent,
    tools=self.tools,
    memory=self.memory,
    verbose=True,  # Change to True
    handle_parsing_errors=True,
    max_iterations=8,
    max_execution_time=60,
)
```

## 📊 Data Schema

### Master Table Sheet
- `Member ID`: Unique identifier
- `Full Name`: Member's full name
- `Email`: Member's email address
- `Address`: Member's address
- `Join Date`: Membership start date
- `Membership Type`: Type of membership (Student, Pharmacist, etc.)
- `Graduation Year`: Year of graduation (for students)
- `Expiration Date`: When membership expires
- `Engagement Score`: Member engagement rating (0-100)

### Payment Table
- `Member ID (PK)`: Reference to member
- `Payment Method`: Payment method used
- `Last Payment Amount`: Amount of last payment

### Feedback Table
- `Member ID`: Reference to member
- `Email`: Member's email
- `Rating`: 1-5 star rating
- `Feedback`: Optional feedback text
- `Date`: Feedback date
- `Service`: Service being rated

## 🆕 Member Profile Management Features

### Profile Update Workflow
1. **Authentication**: User provides email for identification
2. **Profile Display**: Shows current profile information
3. **Field Selection**: User chooses what to update (email, address, graduation year)
4. **Validation**: Input validation for format and data types
5. **Update**: Saves changes to Excel file
6. **Transition Logic**: Suggests membership transitions based on graduation year
7. **Payment Processing**: Simulates payment for transitions
8. **Feedback Collection**: Collects user experience rating

### Graduation Year Logic
- If graduation year becomes 2023+ and member type is "Student"
- Suggests Pharmacist Transition Package ($100, Early Bird $90)
- Updates membership type automatically

### Validation Features
- Email format validation
- Graduation year range validation (1900-2030)
- Address format acceptance
- Error handling and user feedback

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
1. Check the troubleshooting section
2. Review the tool documentation
3. Open an issue on GitHub

---

**Membuddy** - Your intelligent membership management assistant! 🤖 