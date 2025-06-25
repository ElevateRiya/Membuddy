from langchain_core.tools import tool
import pandas as pd
import os
import re
from datetime import datetime
from langchain_core.pydantic_v1 import BaseModel, Field
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Absolute path to the data file
script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(script_dir, '..', 'data', 'AI Agent Data.xlsx')

def get_dataframes():
    """Load Excel data and return dictionary of dataframes."""
    try:
        if not os.path.exists(DATA_FILE):
            logger.error(f"Data file not found at: {os.path.abspath(DATA_FILE)}")
            raise FileNotFoundError(f"The data file was not found. Attempted to use path: {os.path.abspath(DATA_FILE)}")
        
        logger.info(f"Loading data from: {DATA_FILE}")
        xls = pd.ExcelFile(DATA_FILE)
        logger.info(f"Available sheets: {xls.sheet_names}")
        
        dataframes = {}
        for sheet_name in xls.sheet_names:
            try:
                df = pd.read_excel(DATA_FILE, sheet_name=sheet_name)
                dataframes[sheet_name] = df
                logger.info(f"Loaded sheet '{sheet_name}' with {len(df)} rows")
            except Exception as e:
                logger.error(f"Error loading sheet '{sheet_name}': {e}")
                
        return dataframes
    except Exception as e:
        logger.error(f"Error loading Excel file: {e}")
        raise

def save_dataframes(dataframes, filename=None):
    """Save dataframes back to Excel file safely."""
    if filename is None:
        filename = DATA_FILE
    
    try:
        # Create a backup
        backup_file = filename.replace('.xlsx', '_backup.xlsx')
        if os.path.exists(filename):
            import shutil
            shutil.copy2(filename, backup_file)
        
        # Save all sheets
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for sheet_name, df in dataframes.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"Saved data to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        # Try to restore from backup
        if os.path.exists(backup_file):
            import shutil
            shutil.copy2(backup_file, filename)
            logger.info("Restored from backup")
        return False

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

def find_email_column(df):
    """Find the email column in a dataframe."""
    possible_email_cols = ['Email', 'email', 'Email Address', 'email_address', 'E-mail', 'e-mail']
    for col in possible_email_cols:
        if col in df.columns:
            return col
    
    # If exact match not found, look for columns containing 'email'
    for col in df.columns:
        if 'email' in col.lower():
            return col
    
    return None

def normalize_email(email):
    """Normalize email for comparison."""
    if pd.isna(email):
        return ""
    return str(email).strip().lower()

def safe_string_comparison(df_series, target_value):
    """Safely compare strings in a pandas series."""
    try:
        # Convert both to string and normalize
        df_normalized = df_series.astype(str).str.strip().str.lower()
        target_normalized = str(target_value).strip().lower()
        return df_normalized == target_normalized
    except Exception as e:
        logger.error(f"Error in string comparison: {e}")
        return pd.Series([False] * len(df_series))

# TOOL DEFINITIONS

class GetProfileInput(BaseModel):
    email: str = Field(description="The email address of the member.")

@tool(args_schema=GetProfileInput)
def get_member_profile(email: str) -> str:
    """Fetch a member's profile from the Master Table using their email address."""
    logger.info(f"Getting profile for email: {email}")
    
    try:
        dfs = get_dataframes()
        master_df = dfs.get("Master Table")
        
        if master_df is None:
            return "Error: 'Master Table' sheet not found in the data file."
        
        email_col = find_email_column(master_df)
        if not email_col:
            return "Error: Email column not found in Master Table."
        
        logger.info(f"Looking for email in column: {email_col}")
        
        # Use safe string comparison
        member_mask = safe_string_comparison(master_df[email_col], email)
        member_data = master_df[member_mask]
        
        if member_data.empty:
            available_emails = master_df[email_col].dropna().astype(str).str.strip().tolist()[:5]
            logger.info(f"Available emails (first 5): {available_emails}")
            return f"No member found with email: {email}. Please check the email address and try again."
        
        # Convert to dictionary and clean up
        member_dict = member_data.iloc[0].to_dict()
        
        # Format the response nicely
        profile_info = {
            "message": "Member profile found successfully!",
            "profile": {
                "Full Name": member_dict.get('Full Name', 'N/A'),
                "Email": member_dict.get(email_col, 'N/A'),
                "Address": member_dict.get('Address', 'N/A'),
                "Graduation Year": member_dict.get('Graduation Year', 'N/A'),
                "Membership Type": member_dict.get('Membership Type', 'N/A'),
                "Join Date": member_dict.get('Join Date', 'N/A'),
                "Expiration Date": member_dict.get('Expiration Date', 'N/A'),
                "Member ID": member_dict.get('Member ID', 'N/A')
            }
        }
        
        logger.info(f"Found member: {member_dict.get('Full Name', 'Unknown')}")
        return str(profile_info)
        
    except Exception as e:
        logger.error(f"Error getting member profile: {e}")
        return f"Error retrieving member profile: {str(e)}"

class GetRenewalInput(BaseModel):
    email: str = Field(description="The email address of the member.")

@tool(args_schema=GetRenewalInput)
def get_renewal_options(email: str) -> str:
    """Return available renewal options and discounts for the member."""
    logger.info(f"Getting renewal options for email: {email}")
    
    try:
        # Get member profile data directly
        dfs = get_dataframes()
        master_df = dfs.get("Master Table")
        
        if master_df is None:
            return "Error: 'Master Table' sheet not found."
        
        email_col = find_email_column(master_df)
        if not email_col:
            return "Error: Email column not found."
        
        # Find member
        member_mask = safe_string_comparison(master_df[email_col], email)
        member_data = master_df[member_mask]
        
        if member_data.empty:
            return f"No member found with email: {email}"
        
        member_info = member_data.iloc[0].to_dict()
        grad_year = member_info.get("Graduation Year")
        member_type = member_info.get("Membership Type")
        expiration = member_info.get("Expiration Date")
        
        # Convert graduation year to int if it's a string
        try:
            if grad_year is not None:
                grad_year = int(float(grad_year))
        except (ValueError, TypeError):
            grad_year = None
        
        # Renewal logic based on member type and graduation year
        renewal_options = {
            "message": f"Membership expires on {expiration}.",
            "packages": []
        }
        
        if grad_year and grad_year >= 2023 and member_type == "Student":
            renewal_options["message"] += " You're eligible for the Pharmacist Transition Package!"
            renewal_options["packages"] = [{
                "name": "Pharmacist Transition Package",
                "price": 100,
                "early_bird_price": 90,
                "early_bird_deadline": "June 15, 2025",
                "description": "Perfect for recent graduates transitioning to professional practice"
            }]
        elif member_type == "Pharmacist Regular":
            renewal_options["message"] += " Regular renewal available with early bird discount!"
            renewal_options["packages"] = [{
                "name": "Regular Renewal",
                "price": 200,
                "early_bird_price": 180,
                "early_bird_deadline": "June 20, 2025",
                "description": "Annual membership renewal for practicing pharmacists"
            }]
        elif member_type == "Student":
            renewal_options["message"] += " Student renewal available!"
            renewal_options["packages"] = [{
                "name": "Student Renewal",
                "price": 50,
                "early_bird_price": 45,
                "early_bird_deadline": "June 30, 2025",
                "description": "Discounted rate for current students"
            }]
        else:
            renewal_options["message"] += " Please contact support for renewal options specific to your membership type."
        
        return str(renewal_options)
        
    except Exception as e:
        logger.error(f"Error getting renewal options: {e}")
        return f"Error retrieving renewal options: {str(e)}"

class GetPaymentMethodsInput(BaseModel):
    email: str = Field(description="The email address of the member.")

@tool(args_schema=GetPaymentMethodsInput)
def get_payment_methods(email: str) -> str:
    """Fetch available payment methods for a user from the Payment Table using their email."""
    logger.info(f"Getting payment methods for email: {email}")
    
    try:
        dfs = get_dataframes()
        payment_df = dfs.get("Payment Table")
        master_df = dfs.get("Master Table")
        
        if payment_df is None or master_df is None:
            return "Error: Payment Table or Master Table not found."
        
        # Find member ID from email
        email_col = find_email_column(master_df)
        if not email_col:
            return "Error: Email column not found in Master Table."
        
        member_mask = safe_string_comparison(master_df[email_col], email)
        member_row = master_df[member_mask]
        
        if member_row.empty:
            return f"No member found with email: {email}"
        
        member_id = member_row.iloc[0].get("Member ID")
        
        # Find payment methods for this member
        payment_mask = payment_df["Member ID (PK)"].astype(str) == str(member_id)
        payment_rows = payment_df[payment_mask]
        
        if payment_rows.empty:
            # Return default payment methods if none found
            default_methods = ["Card", "ACH", "PayPal"]
            return str({"payment_methods": default_methods})
        
        methods = payment_rows["Payment Method"].dropna().unique().tolist()
        
        # Add default methods if not present
        default_methods = ["Card", "ACH", "PayPal"]
        for method in default_methods:
            if method not in methods:
                methods.append(method)
        
        return str({"payment_methods": methods})
        
    except Exception as e:
        logger.error(f"Error getting payment methods: {e}")
        return f"Error retrieving payment methods: {str(e)}"

class ProcessPaymentInput(BaseModel):
    email: str = Field(description="The email address of the member.")
    payment_method: str = Field(description="The payment method to use.")
    amount: float = Field(description="The payment amount.")

@tool(args_schema=ProcessPaymentInput)
def process_payment(email: str, payment_method: str, amount: float) -> str:
    """
    Simulate payment processing for membership transitions or renewals.
    Updates payment records and returns confirmation.
    """
    logger.info(f"Processing payment for {email}: ${amount} via {payment_method}")
    
    try:
        # Load data
        dfs = get_dataframes()
        master_df = dfs.get("Master Table")
        payment_df = dfs.get("Payment Table")
        
        if master_df is None:
            return "Error: Master Table not found."
        
        # Find member by email
        email_col = find_email_column(master_df)
        if not email_col:
            return "Error: Email column not found."
        
        member_mask = safe_string_comparison(master_df[email_col], email)
        member_row = master_df[member_mask]
        
        if member_row.empty:
            return f"No member found with email: {email}"
        
        member_id = member_row.iloc[0].get("Member ID")
        
        # Create or update payment record
        new_payment_record = {
            "Member ID (PK)": member_id,
            "Payment Method": payment_method,
            "Last Payment Amount": amount,
            "Payment Date": datetime.now().strftime("%Y-%m-%d"),
            "Status": "Completed"
        }
        
        # Add new payment record
        if payment_df is not None:
            payment_df = pd.concat([payment_df, pd.DataFrame([new_payment_record])], ignore_index=True)
            dfs["Payment Table"] = payment_df
        else:
            # Create new payment table if it doesn't exist
            dfs["Payment Table"] = pd.DataFrame([new_payment_record])
        
        # Update member's expiration date (add 1 year from current expiration or today)
        current_expiration = member_row.iloc[0].get("Expiration Date")
        try:
            if pd.notna(current_expiration):
                if isinstance(current_expiration, str):
                    exp_date = pd.to_datetime(current_expiration)
                else:
                    exp_date = current_expiration
                new_expiration = exp_date + pd.DateOffset(years=1)
            else:
                new_expiration = pd.Timestamp.now() + pd.DateOffset(years=1)
            
            master_df.loc[member_mask, "Expiration Date"] = new_expiration.strftime("%Y-%m-%d")
            dfs["Master Table"] = master_df
        except Exception as e:
            logger.error(f"Error updating expiration date: {e}")
        
        # Save updated data
        success = save_dataframes(dfs)
        if not success:
            return "Payment processed but there was an error saving the records. Please contact support."
        
        payment_confirmation = {
            "message": "Payment processed successfully!",
            "details": {
                "Amount": f"${amount:.2f}",
                "Method": payment_method,
                "Status": "Completed",
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Transaction_ID": f"TXN_{member_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        }
        
        return str(payment_confirmation)
        
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        return f"Error processing payment: {str(e)}"

# Smart wrapper tools
class SmartProcessPaymentInput(BaseModel):
    email: str = Field(description="The email address of the member.")
    user_input: str = Field(description="Natural language input from the user about payment.", default="")

@tool(args_schema=SmartProcessPaymentInput)
def smart_process_payment(email: str, user_input: str = "") -> str:
    """
    Smart payment processing tool that extracts payment method from natural language input.
    Handles variations like "use my card", "pay with ACH", etc.
    """
    logger.info(f"Smart payment processing for {email} with input: {user_input}")
    
    try:
        if not user_input or user_input.strip().lower() in ["yes", "ok", "proceed", "continue", "pay"]:
            return ("To proceed with payment, please specify your preferred payment method "
                    "(e.g., 'use card', 'pay with ACH', 'use PayPal') or confirm to use your default payment method.")
        
        # Get available payment methods
        payment_methods_str = get_payment_methods(email)
        
        if "Error" in payment_methods_str:
            return payment_methods_str
        
        # Parse the payment methods
        try:
            import ast
            payment_methods_dict = ast.literal_eval(payment_methods_str)
            available_methods = payment_methods_dict.get("payment_methods", ["Card"])
        except:
            available_methods = ["Card", "ACH", "PayPal"]
        
        # Extract payment method from user input
        payment_method = extract_payment_method(user_input, available_methods)
        
        # Get renewal options to determine amount
        renewal_options_str = get_renewal_options(email)
        
        # Parse renewal options to get amount
        amount = 100.0  # Default amount
        try:
            import ast
            renewal_dict = ast.literal_eval(renewal_options_str)
            packages = renewal_dict.get("packages", [])
            if packages:
                # Use early bird price if available, otherwise regular price
                package = packages[0]
                amount = package.get("early_bird_price", package.get("price", 100.0))
        except:
            amount = 100.0
        
        # Process the payment
        result = process_payment(email, payment_method, amount)
        
        return f"Payment processed using {payment_method} for ${amount:.2f}. {result}"
        
    except Exception as e:
        logger.error(f"Error in smart payment processing: {e}")
        return f"Error in smart payment processing: {str(e)}"

if __name__ == "__main__":
    print("--- Diagnostic: Excel Data Access ---")
    try:
        dfs = get_dataframes()
        print("Sheets found:", list(dfs.keys()))
        if 'Master Table' in dfs:
            print("First 5 rows of 'Master Table':")
            print(dfs['Master Table'].head())
            print("\nColumns in Master Table:")
            print(dfs['Master Table'].columns.tolist())
        else:
            print("'Master Table' sheet not found in the Excel file.")
    except Exception as e:
        print(f"Error loading data: {e}")