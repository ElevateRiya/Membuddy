from langchain_core.tools import tool
import pandas as pd
import os
import re
from datetime import datetime
from langchain_core.pydantic_v1 import BaseModel, Field
import logging
import sys

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db_connection import get_database

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper functions for smart tools
def extract_field_to_update(text: str) -> str:
    """Extract the field to update from natural language input."""
    text_lower = text.lower()
    if any(word in text_lower for word in ['email', 'e-mail', 'mail']):
        return 'email'
    elif any(word in text_lower for word in ['address', 'location', 'street', 'home']):
        return 'address'
    elif any(word in text_lower for word in ['graduation', 'grad year', 'year', 'graduate']):
        return 'graduation_year'
    else:
        return 'address'  # default

def extract_new_value(text: str, field: str) -> str:
    """Extract the new value from natural language input."""
    if field == 'email':
        # Extract email using regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else ""
    elif field == 'graduation_year':
        # Extract 4-digit year
        year_pattern = r'\b(19|20)\d{2}\b'
        match = re.search(year_pattern, text)
        return match.group(0) if match else ""
    elif field == 'address':
        # Extract address after keywords
        address_keywords = ['address', 'location', 'street', 'home', 'live at', 'move to', 'to']
        text_lower = text.lower()
        for keyword in address_keywords:
            if keyword in text_lower:
                start_idx = text_lower.find(keyword) + len(keyword)
                address = text[start_idx:].strip()
                # Clean up the address - remove common prefixes and punctuation
                address = re.sub(r'^[:\s,]+', '', address)
                # Remove "to" if it appears at the beginning
                address = re.sub(r'^to\s+', '', address, flags=re.IGNORECASE)
                if address:
                    return address
        # If no keyword found, return the whole text as address
        return text.strip()
    return ""

def extract_payment_method(text: str, available_methods: list) -> str:
    """Extract payment method from natural language input."""
    text_lower = text.lower()
    for method in available_methods:
        if method.lower() in text_lower:
            return method
    # Default to first available method if none found
    return available_methods[0] if available_methods else "Card"

# TOOL DEFINITIONS

class GetProfileInput(BaseModel):
    email: str = Field(description="The email address of the member.")

@tool(args_schema=GetProfileInput)
def get_member_profile(email: str) -> str:
    """Fetch a member's profile from the database using their email address."""
    logger.info(f"Getting profile for email: {email}")
    
    try:
        db = get_database()
        member_data = db.get_member_profile(email)
        
        if not member_data:
            return f"No member found with email: {email}. Please check the email address and try again."
        
        # Format the response nicely
        profile_info = {
            "message": "Member profile found successfully!",
            "profile": {
                "Full Name": member_data.get('full_name', 'N/A'),
                "Email": member_data.get('email', 'N/A'),
                "Address": member_data.get('address', 'N/A'),
                "Graduation Year": member_data.get('graduation_year', 'N/A'),
                "Membership Type": member_data.get('membership_type', 'N/A'),
                "Join Date": str(member_data.get('join_date', 'N/A')),
                "Expiration Date": str(member_data.get('expiration_date', 'N/A')),
                "Member ID": member_data.get('member_id', 'N/A'),
                "Status": member_data.get('status', 'N/A'),
                "Phone": member_data.get('phone', 'N/A'),
                "Company": member_data.get('company', 'N/A'),
                "Job Title": member_data.get('job_title', 'N/A'),
                "Department": member_data.get('department', 'N/A'),
                "Membership Level": member_data.get('membership_level', 'N/A'),
                "Benefits": member_data.get('benefits', 'N/A'),
                "Renewal Cycle": member_data.get('renewal_cycle', 'N/A'),
                "Auto Renewal": "Yes" if member_data.get('auto_renewal') else "No",
                "Renewal Amount": f"${member_data.get('renewal_amount', 0):.2f}" if member_data.get('renewal_amount') else 'N/A',
                "Discount Percentage": f"{member_data.get('discount_percentage', 0):.1f}%" if member_data.get('discount_percentage') else '0%'
            }
        }
        
        # Build the response string
        response = f"✅ {profile_info['message']}\n\n"
        response += "**Member Profile:**\n"
        for key, value in profile_info['profile'].items():
            response += f"• **{key}:** {value}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting member profile: {e}")
        return f"Error retrieving member profile: {str(e)}"

class GetRenewalInput(BaseModel):
    email: str = Field(description="The email address of the member.")

@tool(args_schema=GetRenewalInput)
def get_renewal_options(email: str) -> str:
    """Get renewal options and pricing for a member's membership."""
    logger.info(f"Getting renewal options for email: {email}")
    
    try:
        db = get_database()
        renewal_data = db.get_renewal_options(email)
        
        if not renewal_data:
            return f"No active membership found for email: {email}. Please check the email address or contact support."
        
        # Calculate final amount with discount
        base_amount = float(renewal_data.get('renewal_amount', 0))
        discount_percent = float(renewal_data.get('discount_percentage', 0))
        final_amount = base_amount * (1 - discount_percent / 100)
        
        response = f"🔄 **Renewal Options for {renewal_data.get('full_name', 'Member')}**\n\n"
        response += f"**Current Membership:**\n"
        response += f"• **Type:** {renewal_data.get('membership_type', 'N/A')}\n"
        response += f"• **Level:** {renewal_data.get('membership_level', 'N/A')}\n"
        response += f"• **Expiration Date:** {str(renewal_data.get('expiration_date', 'N/A'))}\n"
        response += f"• **Renewal Cycle:** {renewal_data.get('renewal_cycle', 'N/A')}\n\n"
        
        response += f"**Pricing:**\n"
        response += f"• **Base Amount:** ${base_amount:.2f}\n"
        if discount_percent > 0:
            response += f"• **Discount:** {discount_percent:.1f}%\n"
            response += f"• **Final Amount:** ${final_amount:.2f}\n"
        else:
            response += f"• **Final Amount:** ${base_amount:.2f}\n"
        
        response += f"\n**Available Payment Methods:**\n"
        payment_methods = db.get_payment_methods(email)
        for method in payment_methods:
            response += f"• {method}\n"
        
        response += f"\nTo proceed with renewal, please specify your preferred payment method and confirm the amount."
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting renewal options: {e}")
        return f"Error retrieving renewal options: {str(e)}"

class GetPaymentMethodsInput(BaseModel):
    email: str = Field(description="The email address of the member.")

@tool(args_schema=GetPaymentMethodsInput)
def get_payment_methods(email: str) -> str:
    """Get available payment methods for a member."""
    logger.info(f"Getting payment methods for email: {email}")
    
    try:
        db = get_database()
        payment_methods = db.get_payment_methods(email)
        
        if not payment_methods:
            return f"No payment history found for {email}. Available payment methods: Card, ACH, PayPal, Check, Bank Transfer"
        
        response = f"💳 **Available Payment Methods for {email}:**\n\n"
        response += "**Previously Used Methods:**\n"
        for method in payment_methods:
            response += f"• {method}\n"
        
        response += f"\n**All Available Methods:**\n"
        all_methods = ['Card', 'ACH', 'PayPal', 'Check', 'Bank Transfer']
        for method in all_methods:
            if method in payment_methods:
                response += f"• {method} ✓ (Previously used)\n"
            else:
                response += f"• {method}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting payment methods: {e}")
        return f"Error retrieving payment methods: {str(e)}"

class ProcessPaymentInput(BaseModel):
    email: str = Field(description="The email address of the member.")
    payment_method: str = Field(description="The payment method to use.")
    amount: float = Field(description="The payment amount.")

@tool(args_schema=ProcessPaymentInput)
def process_payment(email: str, payment_method: str, amount: float) -> str:
    """Process a payment for a member's membership renewal."""
    logger.info(f"Processing payment for {email}: {payment_method}, ${amount}")
    
    try:
        db = get_database()
        
        # Validate payment method
        valid_methods = ['Card', 'ACH', 'PayPal', 'Check', 'Bank Transfer']
        if payment_method not in valid_methods:
            return f"Invalid payment method: {payment_method}. Please choose from: {', '.join(valid_methods)}"
        
        # Process the payment
        description = f"Membership renewal payment via {payment_method}"
        transaction_id = db.process_payment(email, payment_method, amount, description)
        
        if transaction_id:
            response = f"✅ **Payment Processed Successfully!**\n\n"
            response += f"**Transaction Details:**\n"
            response += f"• **Member:** {email}\n"
            response += f"• **Amount:** ${amount:.2f}\n"
            response += f"• **Payment Method:** {payment_method}\n"
            response += f"• **Transaction ID:** {transaction_id}\n"
            response += f"• **Status:** Completed\n\n"
            response += f"Your membership has been renewed! You will receive a confirmation email shortly."
            
            return response
        else:
            return f"❌ Payment processing failed. Please try again or contact support."
        
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        return f"Error processing payment: {str(e)}"

class SmartProcessPaymentInput(BaseModel):
    email: str = Field(description="The email address of the member.")
    user_input: str = Field(description="Natural language input from the user about payment.", default="")

@tool(args_schema=SmartProcessPaymentInput)
def smart_process_payment(email: str, user_input: str = "") -> str:
    """Smart payment processing that extracts payment method and amount from natural language input."""
    logger.info(f"Smart payment processing for {email}: {user_input}")
    
    try:
        db = get_database()
        
        # Get available payment methods
        available_methods = db.get_payment_methods(email)
        if not available_methods:
            available_methods = ['Card', 'ACH', 'PayPal', 'Check', 'Bank Transfer']
        
        # Extract payment method from user input
        payment_method = extract_payment_method(user_input, available_methods)
        
        # Extract amount from user input
        amount_match = re.search(r'\$?(\d+(?:\.\d{2})?)', user_input)
        if amount_match:
            amount = float(amount_match.group(1))
        else:
            # Get renewal amount from database
            renewal_data = db.get_renewal_options(email)
            if renewal_data:
                base_amount = float(renewal_data.get('renewal_amount', 0))
                discount_percent = float(renewal_data.get('discount_percentage', 0))
                amount = base_amount * (1 - discount_percent / 100)
            else:
                return f"Could not determine payment amount. Please specify the amount you'd like to pay."
        
        # Process the payment
        description = f"Membership renewal payment via {payment_method}"
        transaction_id = db.process_payment(email, payment_method, amount, description)
        
        if transaction_id:
            response = f"✅ **Payment Processed Successfully!**\n\n"
            response += f"**Transaction Details:**\n"
            response += f"• **Member:** {email}\n"
            response += f"• **Amount:** ${amount:.2f}\n"
            response += f"• **Payment Method:** {payment_method}\n"
            response += f"• **Transaction ID:** {transaction_id}\n"
            response += f"• **Status:** Completed\n\n"
            response += f"Your membership has been renewed! You will receive a confirmation email shortly."
            
            return response
        else:
            return f"❌ Payment processing failed. Please try again or contact support."
        
    except Exception as e:
        logger.error(f"Error in smart payment processing: {e}")
        return f"Error processing payment: {str(e)}"

if __name__ == "__main__":
    print("--- Diagnostic: Database Connection ---")
    try:
        db = get_database()
        print("Connected to the database.")
    except Exception as e:
        print(f"Error connecting to the database: {e}")