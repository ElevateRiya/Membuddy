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
import json
import sys

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db_connection import get_database

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        address_keywords = ['address', 'location', 'street', 'home', 'live at', 'move to', 'to']
        text_lower = text.lower()
        for keyword in address_keywords:
            if keyword in text_lower:
                start_idx = text_lower.find(keyword) + len(keyword)
                address = text[start_idx:].strip()
                address = re.sub(r'^[:\s,]+', '', address)
                address = re.sub(r'^to\s+', '', address, flags=re.IGNORECASE)
                if address:
                    return address
        # If no keyword found, return the whole text as address
        return text.strip()
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
    user_input: str = Field(description="Natural language input from the user about payment.", default="")

@tool(args_schema=SmartProcessPaymentInput)
def smart_process_payment(email: str, user_input: str = "") -> str:
    """
    Smart payment processing tool that extracts payment method and amount from natural language input.
    Handles variations like "use my card", "pay $100", "use ACH", etc.
    Returns a simple string message instead of complex objects.
    """
    try:
        logger.info(f"Smart payment processing for {email}: {user_input}")
        
        # If no user_input provided, ask for it
        if not user_input or user_input.strip() == "":
            return "Please specify your payment method and amount. For example: 'pay $499.99 with card' or 'use ACH for $499.99'"
        
        cleaned_input = fix_typos(user_input)
        
        db = get_database()
        
        # Get available payment methods
        available_methods = db.get_payment_methods(email)
        if not available_methods:
            available_methods = ['Card', 'ACH', 'PayPal', 'Check', 'Bank Transfer']
        
        # Extract payment method
        payment_method = extract_payment_method(cleaned_input, available_methods)
        if not payment_method:
            return f"Please specify your payment method. Available options: {', '.join(available_methods)}"
        
        # Extract amount
        amount = extract_amount(cleaned_input)
        if not amount:
            # Get renewal amount from database
            renewal_data = db.get_renewal_options(email)
            if renewal_data:
                base_amount = float(renewal_data.get('renewal_amount', 0))
                discount_percent = float(renewal_data.get('discount_percentage', 0))
                amount = base_amount * (1 - discount_percent / 100)
            else:
                return "Please specify the amount you'd like to pay."
        
        # Process payment
        description = f"Membership renewal payment via {payment_method}"
        transaction_id = db.process_payment(email, payment_method, amount, description)
        
        if transaction_id:
            return f"✅ Payment processed successfully! Amount: ${amount:.2f}, Method: {payment_method}, Transaction ID: {transaction_id}"
        else:
            return "❌ Payment processing failed. Please try again or contact support."
        
    except Exception as e:
        logger.error(f"Error in smart payment processing: {e}")
        return f"Error processing payment: {str(e)}"

class UpdateProfileInput(BaseModel):
    email: str = Field(description="The email address of the member.")
    field: str = Field(description="The field to update (email, address, graduation_year).")
    value: str = Field(description="The new value for the field.")

@tool(args_schema=UpdateProfileInput)
def update_profile(email: str, field: str, value: str) -> str:
    """Update a member's profile information."""
    logger.info(f"Updating profile for {email}: {field} = {value}")
    
    try:
        db = get_database()
        
        # Validate the field
        valid_fields = ['email', 'address', 'graduation_year']
        if field not in valid_fields:
            return f"Invalid field: {field}. Please choose from: {', '.join(valid_fields)}"
        
        # Update the profile
        success = db.update_profile(email, field, value)
        
        if success:
            return f"✅ Profile updated successfully! {field} has been changed to: {value}"
        else:
            return f"❌ Failed to update profile. Please try again or contact support."
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return f"Error updating profile: {str(e)}"

class CollectFeedbackInput(BaseModel):
    rating: int = Field(description="The rating from 1 to 5 stars.")
    comment: Optional[str] = Field(description="Optional feedback comment.", default="")
    email: str = Field(description="The email address of the member (optional for anonymous feedback).", default="")

@tool(args_schema=CollectFeedbackInput)
def collect_feedback(rating: int, comment: str = "", email: str = "") -> str:
    """Collect feedback from a member."""
    logger.info(f"Collecting feedback: rating={rating}, comment={comment}, email={email}")
    
    try:
        db = get_database()
        
        # Validate rating
        if rating < 1 or rating > 5:
            return "Invalid rating. Please provide a rating between 1 and 5."
        
        # Collect feedback
        feedback_id = db.collect_feedback(rating, comment, email)
        
        if feedback_id:
            return f"✅ Thank you for your feedback! Your rating of {rating} stars has been recorded."
        else:
            return "❌ Failed to record feedback. Please try again."
        
    except Exception as e:
        logger.error(f"Error collecting feedback: {e}")
        return f"Error collecting feedback: {str(e)}"