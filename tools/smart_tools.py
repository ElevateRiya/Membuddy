from langchain_core.tools import tool
from langchain_core.pydantic_v1 import BaseModel, Field
import pandas as pd
import os
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from difflib import get_close_matches
import functools

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Absolute path to the data file
script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(script_dir, '..', 'data', 'AI Agent Data.xlsx')

# Cache for Excel data
_dataframes_cache = None
_cache_timestamp = None

@functools.lru_cache(maxsize=1)
def get_dataframes_cached():
    """Cached version of get_dataframes to improve performance"""
    global _dataframes_cache, _cache_timestamp
    current_time = datetime.now()
    if (_dataframes_cache is not None and _cache_timestamp is not None and (current_time - _cache_timestamp).seconds < 300):
        return _dataframes_cache
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"The data file was not found. Attempted to use path: {os.path.abspath(DATA_FILE)}")
    xls = pd.ExcelFile(DATA_FILE)
    _dataframes_cache = {sheet_name: xls.parse(sheet_name) for sheet_name in xls.sheet_names}
    _cache_timestamp = current_time
    return _dataframes_cache

def clear_dataframes_cache():
    global _dataframes_cache, _cache_timestamp
    _dataframes_cache = None
    _cache_timestamp = None
    get_dataframes_cached.cache_clear()

def extract_email(text: str) -> Optional[str]:
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)
    return match.group(0) if match else None

def extract_amount(text: str) -> Optional[float]:
    amount_patterns = [
        r'\$(\d+(?:\.\d{2})?)',
        r'(\d+(?:\.\d{2})?)\s*dollars?',
        r'(\d+(?:\.\d{2})?)\s*bucks?',
        r'(\d+(?:\.\d{2})?)',
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                continue
    return None

def extract_payment_method(text: str, available_methods: list) -> Optional[str]:
    text_lower = text.lower()
    for method in available_methods:
        if method.lower() in text_lower:
            return method
    payment_keywords = {
        'card': ['card', 'credit', 'debit', 'visa', 'mastercard'],
        'ach': ['ach', 'bank', 'direct debit', 'transfer'],
        'paypal': ['paypal', 'pay pal'],
        'check': ['check', 'cheque']
    }
    for method in available_methods:
        method_lower = method.lower()
        for keyword, variations in payment_keywords.items():
            if any(var in method_lower for var in variations):
                if any(var in text_lower for var in variations):
                    return method
    if available_methods:
        matches = get_close_matches(text_lower, [m.lower() for m in available_methods], n=1, cutoff=0.6)
        if matches:
            for method in available_methods:
                if method.lower() == matches[0]:
                    return method
    return None

def extract_field_to_update(text: str) -> Optional[str]:
    text_lower = text.lower()
    field_mapping = {
        'email': ['email', 'e-mail', 'mail'],
        'address': ['address', 'location', 'street', 'home'],
        'graduation_year': ['graduation', 'grad year', 'year', 'graduate', 'graduated']
    }
    for field, keywords in field_mapping.items():
        if any(keyword in text_lower for keyword in keywords):
            return field
    return None

def extract_new_value(text: str, field: str) -> Optional[str]:
    if field == 'email':
        return extract_email(text)
    elif field == 'graduation_year':
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        return year_match.group(0) if year_match else None
    elif field == 'address':
        address_keywords = ['address', 'location', 'street', 'home', 'live at', 'move to']
        text_lower = text.lower()
        for keyword in address_keywords:
            if keyword in text_lower:
                start_idx = text_lower.find(keyword) + len(keyword)
                address = text[start_idx:].strip()
                address = re.sub(r'^[:\s,]+', '', address)
                if address:
                    return address
        words = text.split()
        if len(words) >= 3:
            return text
    return None

def validate_input(text: str, field: str) -> Dict[str, Any]:
    result = {"valid": True, "message": "", "suggestions": []}
    if field == 'email':
        email = extract_email(text)
        if not email:
            result["valid"] = False
            result["message"] = "I couldn't find a valid email address. Please provide your email in the format: user@example.com"
            result["suggestions"] = ["Please enter a valid email address"]
    elif field == 'graduation_year':
        year = extract_new_value(text, field)
        if not year:
            result["valid"] = False
            result["message"] = "I couldn't find a valid graduation year. Please provide a 4-digit year (e.g., 2023)"
            result["suggestions"] = ["Please enter a 4-digit year like 2023"]
        else:
            try:
                year_int = int(year)
                if year_int < 1900 or year_int > 2030:
                    result["valid"] = False
                    result["message"] = f"Graduation year {year} seems unusual. Please provide a year between 1900 and 2030."
                    result["suggestions"] = [f"Please enter a year between 1900 and 2030"]
            except ValueError:
                result["valid"] = False
                result["message"] = "Please provide a valid 4-digit year"
                result["suggestions"] = ["Please enter a 4-digit year like 2023"]
    elif field == 'address':
        address = extract_new_value(text, field)
        if not address or len(address.strip()) < 5:
            result["valid"] = False
            result["message"] = "I couldn't find a complete address. Please provide your full address including street number and city."
            result["suggestions"] = ["Please provide your complete address"]
    return result

def fix_typos(text: str) -> str:
    typo_fixes = {
        'membreshi': 'membership',
        'membeship': 'membership',
        'renue': 'renew',
        'renuew': 'renew',
        'updte': 'update',
        'updat': 'update',
        'proflie': 'profile',
        'profil': 'profile',
        'paymnt': 'payment',
        'paymet': 'payment',
        'adres': 'address',
        'adress': 'address',
        'emai': 'email',
        'emial': 'email',
        'gradution': 'graduation',
        'graduat': 'graduation',
    }
    words = text.split()
    fixed_words = []
    for word in words:
        word_lower = word.lower()
        if word_lower in typo_fixes:
            fixed_words.append(typo_fixes[word_lower])
        else:
            fixed_words.append(word)
    return ' '.join(fixed_words)

class SmartProcessPaymentInput(BaseModel):
    email: str = Field(description="The email address of the member.")
    user_input: str = Field(description="Natural language input from the user about payment.")

@tool(args_schema=SmartProcessPaymentInput)
def smart_process_payment(email: str, user_input: str) -> str:
    """
    Smart payment processing tool that extracts payment method and amount from natural language input.
    Handles variations like "use my card", "pay $100", "use ACH", etc.
    """
    try:
        logger.info(f"Smart payment processing for {email}: {user_input}")
        cleaned_input = fix_typos(user_input)
        logger.info(f"Cleaned input: {cleaned_input}")
        dfs = get_dataframes_cached()
        payment_df = dfs.get("Payment Table")
        master_df = dfs.get("Master Table")
        if payment_df is None or master_df is None:
            return "Error: Required data sheets not found."
        email_col = next((col for col in master_df.columns if 'Email' in col), None)
        if not email_col:
            return "Error: Email column not found."
        member_row = master_df[master_df[email_col].str.strip() == email.strip()]
        if member_row.empty:
            return f"No member found with email: {email}"
        member_id = member_row.iloc[0].get("Member ID")
        payment_rows = payment_df[payment_df["Member ID (PK)"].astype(str) == str(member_id)]
        if payment_rows.empty():
            return "No payment methods found for this member. Please add a payment method first."
        available_methods = payment_rows["Payment Method"].dropna().unique().tolist()
        payment_method = extract_payment_method(cleaned_input, available_methods)
        if not payment_method:
            return f"I couldn't identify your payment method. Your available methods are: {', '.join(available_methods)}. Please specify which one you'd like to use."
        amount = extract_amount(cleaned_input)
        if not amount:
            amount = 100.0
            return f"I'll use your {payment_method} to process a payment of ${amount:.2f}. Is this correct?"
        new_payment_record = {
            "Member ID (PK)": member_id,
            "Payment Method": payment_method,
            "Last Payment Amount": amount,
            "Payment Date": datetime.now().strftime("%Y-%m-%d"),
            "Status": "Completed"
        }
        payment_df = pd.concat([payment_df, pd.DataFrame([new_payment_record])], ignore_index=True)
        with pd.ExcelWriter(DATA_FILE, mode='a', if_sheet_exists='replace') as writer:
            payment_df.to_excel(writer, sheet_name='Payment Table', index=False)
        clear_dataframes_cache()
        return {
            "message": f"Payment processed successfully using {payment_method}!",
            "details": {
                "Amount": f"${amount:.2f}",
                "Method": payment_method,
                "Status": "Completed",
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    except Exception as e:
        logger.error(f"Error in smart_process_payment: {e}")
        return f"Error processing payment: {str(e)}"

class SmartUpdateProfileInput(BaseModel):
    email: str = Field(description="The email address of the member.")
    user_input: str = Field(description="Natural language input from the user about what to update.")

@tool(args_schema=SmartUpdateProfileInput)
def smart_update_profile(email: str, user_input: str) -> str:
    """
    Smart profile update tool that extracts field and value from natural language input.
    Handles variations like "update my graduation year to 2023", "change my address to 123 Main St", etc.
    """
    try:
        logger.info(f"Smart profile update for {email}: {user_input}")
        cleaned_input = fix_typos(user_input)
        logger.info(f"Cleaned input: {cleaned_input}")
        field = extract_field_to_update(cleaned_input)
        if not field:
            return "I couldn't understand what you want to update. Please specify: email, address, or graduation year."
        new_value = extract_new_value(cleaned_input, field)
        if not new_value:
            return f"I couldn't find the new value for your {field}. Please provide the new {field}."
        validation = validate_input(cleaned_input, field)
        if not validation["valid"]:
            return validation["message"]
        dfs = get_dataframes_cached()
        master_df = dfs.get("Master Table")
        if master_df is None:
            return "Error: 'Master Table' sheet not found."
        email_col = next((col for col in master_df.columns if 'Email' in col), None)
        if not email_col:
            return "Error: Email column not found."
        member_mask = master_df[email_col].str.strip() == email.strip()
        if not member_mask.any():
            return f"No member found with email: {email}"
        member_idx = member_mask.idxmax()
        current_data = master_df.loc[member_idx].copy()
        field_mapping = {
            'email': email_col,
            'address': 'Address',
            'graduation_year': 'Graduation Year'
        }
        excel_column = field_mapping[field]
        if excel_column not in master_df.columns:
            return f"Error: Column '{excel_column}' not found in Master Table."
        if field == 'graduation_year':
            master_df.loc[member_idx, excel_column] = int(new_value)
        else:
            master_df.loc[member_idx, excel_column] = new_value
        transition_message = ""
        if field == 'graduation_year':
            new_year = int(new_value)
            current_type = current_data.get('Membership Type', '')
            if new_year >= 2023 and current_type == 'Student':
                transition_message = f"\n\n🎓 Graduation Year Update: Since your graduation year is now {new_year} and you're currently a Student member, you're eligible for the Pharmacist Transition Package ($100, Early Bird $90 before June 15)."
        with pd.ExcelWriter(DATA_FILE, mode='a', if_sheet_exists='replace') as writer:
            master_df.to_excel(writer, sheet_name='Master Table', index=False)
        clear_dataframes_cache()
        updated_data = master_df.loc[member_idx].to_dict()
        profile_summary = {
            "message": f"Successfully updated {field} to: {new_value}",
            "updated_profile": {
                "Full Name": updated_data.get('Full Name', 'N/A'),
                "Email": updated_data.get(email_col, 'N/A'),
                "Address": updated_data.get('Address', 'N/A'),
                "Graduation Year": updated_data.get('Graduation Year', 'N/A'),
                "Membership Type": updated_data.get('Membership Type', 'N/A'),
                "Join Date": updated_data.get('Join Date', 'N/A'),
                "Expiration Date": updated_data.get('Expiration Date', 'N/A')
            }
        }
        if transition_message:
            profile_summary["transition_offer"] = transition_message
        return profile_summary
    except Exception as e:
        logger.error(f"Error in smart_update_profile: {e}")
        return f"Error updating profile: {str(e)}"

class CollectFeedbackInput(BaseModel):
    rating: int = Field(description="The rating from 1 to 5 stars.")
    comment: Optional[str] = Field(description="Optional feedback comment.", default="")

@tool(args_schema=CollectFeedbackInput)
def collect_feedback(rating: int, comment: str = "") -> str:
    """
    Collect and log user feedback for engagement scoring.
    Updates the Feedback Table with rating and optional text.
    """
    try:
        if not 1 <= rating <= 5:
            return "Error: Rating must be between 1 and 5."
        email = "user@example.com"  # Should be set from context in real use
        dfs = get_dataframes_cached()
        master_df = dfs.get("Master Table")
        feedback_df = dfs.get("Feedback Table")
        if master_df is None:
            return "Error: Master Table not found."
        email_col = next((col for col in master_df.columns if 'Email' in col), None)
        if not email_col:
            return "Error: Email column not found."
        member_row = master_df[master_df[email_col].str.strip() == email.strip()]
        if member_row.empty:
            return f"No member found with email: {email}"
        member_id = member_row.iloc[0].get("Member ID")
        feedback_record = {
            "Member ID": member_id,
            "Email": email,
            "Rating": rating,
            "Feedback": comment,
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Service": "Profile Management"
        }
        if feedback_df is not None:
            feedback_df = pd.concat([feedback_df, pd.DataFrame([feedback_record])], ignore_index=True)
        else:
            feedback_df = pd.DataFrame([feedback_record])
        with pd.ExcelWriter(DATA_FILE, mode='a', if_sheet_exists='replace') as writer:
            feedback_df.to_excel(writer, sheet_name='Feedback Table', index=False)
        if len(feedback_df) > 0:
            avg_rating = feedback_df['Rating'].mean()
            engagement_score = min(100, int(avg_rating * 20))
            master_df.loc[master_df[email_col].str.strip() == email.strip(), 'Engagement Score'] = engagement_score
            with pd.ExcelWriter(DATA_FILE, mode='a', if_sheet_exists='replace') as writer:
                master_df.to_excel(writer, sheet_name='Master Table', index=False)
        clear_dataframes_cache()
        return {
            "message": f"Thank you for your feedback! Your {rating}-star rating has been recorded.",
            "engagement_score": engagement_score if 'engagement_score' in locals() else "N/A"
        }
    except Exception as e:
        logger.error(f"Error in collect_feedback: {e}")
        return f"Error collecting feedback: {str(e)}"

class DebugInputsInput(BaseModel):
    tool_name: str = Field(description="Name of the tool being debugged.")
    extracted_args: Dict[str, Any] = Field(description="Extracted arguments from user input.")
    missing_fields: list = Field(description="List of missing required fields.")

@tool(args_schema=DebugInputsInput)
def debug_inputs(tool_name: str, extracted_args: Dict[str, Any], missing_fields: list) -> str:
    """
    Debug tool for logging tool inputs and missing fields during development.
    """
    debug_info = {
        "tool_name": tool_name,
        "extracted_args": extracted_args,
        "missing_fields": missing_fields,
        "timestamp": datetime.now().isoformat()
    }
    logger.info(f"Debug info: {debug_info}")
    return {
        "debug_info": debug_info,
        "message": f"Debug information logged for {tool_name}. Missing fields: {missing_fields}"
    } 