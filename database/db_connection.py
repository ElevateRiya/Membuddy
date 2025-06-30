import pyodbc
import pymssql
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "1433")  # default MSSQL port

class DatabaseConnection:
    """Database connection class for Membuddy application using Microsoft SQL Server."""
    
    def __init__(self):
        self.connection = None
        self.config = {
            'server': DB_HOST,
            'database': DB_NAME,
            'user': DB_USER,
            'password': DB_PASSWORD,
            'port': int(DB_PORT),
            'charset': 'utf8',
            'autocommit': True
        }
    
    def connect(self):
        """Establish database connection."""
        try:
            # Try pyodbc first (more reliable for Azure SQL)
            connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.config['server']};DATABASE={self.config['database']};UID={self.config['user']};PWD={self.config['password']};TrustServerCertificate=yes;"
            self.connection = pyodbc.connect(connection_string)
            logger.info("Database connection established successfully using pyodbc")
            return True
        except Exception as e:
            try:
                # Fallback to pymssql
                self.connection = pymssql.connect(
                    server=self.config['server'],
                    database=self.config['database'],
                    user=self.config['user'],
                    password=self.config['password'],
                    port=self.config['port']
                )
                logger.info("Database connection established successfully using pymssql")
                return True
            except Exception as e2:
                logger.error(f"Error connecting to database: {e2}")
                return False
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
        """Execute a SELECT query and return results."""
        try:
            if not self.connection:
                if not self.connect():
                    return None
            
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Get column names
            columns = [column[0] for column in cursor.description]
            
            # Fetch all rows and convert to list of dictionaries
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return None
    
    def execute_procedure(self, procedure_name: str, params: tuple = None) -> Optional[List[Dict]]:
        """Execute a stored procedure and return results."""
        try:
            if not self.connection:
                if not self.connect():
                    return None
            
            cursor = self.connection.cursor()
            
            # Build the procedure call
            if params:
                param_placeholders = ','.join(['?' for _ in params])
                call = f"EXEC {procedure_name} {param_placeholders}"
                cursor.execute(call, params)
            else:
                call = f"EXEC {procedure_name}"
                cursor.execute(call)
            
            # Get column names
            columns = [column[0] for column in cursor.description] if cursor.description else []
            
            # Fetch all rows and convert to list of dictionaries
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Error executing procedure {procedure_name}: {e}")
            return None
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute an INSERT, UPDATE, or DELETE query."""
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Error executing update: {e}")
            return False

class MembuddyDatabase:
    """Main database operations class for Membuddy."""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def get_member_profile(self, email: str) -> Optional[Dict]:
        """Get member profile by email."""
        try:
            results = self.db.execute_procedure('membuddy.GetMemberProfile', (email,))
            if results and len(results) > 0:
                return results[0]
            return None
        except Exception as e:
            logger.error(f"Error getting member profile: {e}")
            return None
    
    def get_renewal_options(self, email: str) -> Optional[Dict]:
        """Get renewal options for a member."""
        try:
            results = self.db.execute_procedure('membuddy.GetRenewalOptions', (email,))
            if results and len(results) > 0:
                return results[0]
            return None
        except Exception as e:
            logger.error(f"Error getting renewal options: {e}")
            return None
    
    def process_payment(self, email: str, payment_method: str, amount: float, description: str) -> Optional[str]:
        """Process a payment for a member."""
        try:
            results = self.db.execute_procedure('membuddy.ProcessPayment', (email, payment_method, amount, description))
            if results and len(results) > 0:
                return results[0].get('transaction_id')
            return None
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return None
    
    def collect_feedback(self, rating: int, comment: str = "", email: str = "") -> Optional[str]:
        """Collect feedback from a member."""
        try:
            # If no email provided, use anonymous feedback
            if not email:
                email = "anonymous@membuddy.com"
            
            # Insert feedback and get the ID
            query = """
                INSERT INTO membuddy.feedback (member_id, rating, comment, feedback_date, feedback_type)
                VALUES ((SELECT member_id FROM membuddy.master_table WHERE email = ?), ?, ?, GETDATE(), 'General')
            """
            
            if self.db.execute_update(query, (email, rating, comment)):
                # Get the feedback ID
                feedback_query = """
                    SELECT TOP 1 feedback_id 
                    FROM membuddy.feedback 
                    WHERE member_id = (SELECT member_id FROM membuddy.master_table WHERE email = ?)
                    ORDER BY feedback_date DESC
                """
                results = self.db.execute_query(feedback_query, (email,))
                if results:
                    return str(results[0]['feedback_id'])
                return "success"
            return None
        except Exception as e:
            logger.error(f"Error collecting feedback: {e}")
            return None
    
    def update_member_profile(self, email: str, field: str, value: str) -> bool:
        """Update a member's profile field."""
        try:
            # Map field names to database columns
            field_mapping = {
                'email': 'email',
                'address': 'address',
                'graduation_year': 'graduation_year'
            }
            
            if field not in field_mapping:
                logger.error(f"Invalid field: {field}")
                return False
            
            db_field = field_mapping[field]
            query = f"UPDATE membuddy.master_table SET {db_field} = ?, updated_at = GETDATE() WHERE email = ?"
            
            # Handle graduation year as integer
            if field == 'graduation_year':
                try:
                    value = int(value)
                except ValueError:
                    logger.error(f"Invalid graduation year: {value}")
                    return False
            
            return self.db.execute_update(query, (value, email))
        except Exception as e:
            logger.error(f"Error updating member profile: {e}")
            return False
    
    def update_profile(self, email: str, field: str, value: str) -> bool:
        """Alias for update_member_profile to match tool expectations."""
        return self.update_member_profile(email, field, value)
    
    def get_payment_methods(self, email: str) -> List[str]:
        """Get available payment methods for a member."""
        try:
            query = """
                SELECT DISTINCT payment_method 
                FROM membuddy.payments 
                WHERE member_id = (SELECT member_id FROM membuddy.master_table WHERE email = ?)
                AND payment_status = 'Completed'
                ORDER BY payment_date DESC
            """
            results = self.db.execute_query(query, (email,))
            if results:
                return [row['payment_method'] for row in results]
            return ['Card', 'ACH', 'PayPal', 'Check', 'Bank Transfer']  # Default methods
        except Exception as e:
            logger.error(f"Error getting payment methods: {e}")
            return ['Card', 'ACH', 'PayPal', 'Check', 'Bank Transfer']
    
    def get_active_members(self) -> List[Dict]:
        """Get all active members."""
        try:
            query = "SELECT * FROM membuddy.active_members"
            return self.db.execute_query(query) or []
        except Exception as e:
            logger.error(f"Error getting active members: {e}")
            return []
    
    def get_expiring_memberships(self) -> List[Dict]:
        """Get memberships expiring within 30 days."""
        try:
            query = "SELECT * FROM membuddy.expiring_memberships"
            return self.db.execute_query(query) or []
        except Exception as e:
            logger.error(f"Error getting expiring memberships: {e}")
            return []
    
    def get_payment_summary(self, email: str) -> Optional[Dict]:
        """Get payment summary for a member."""
        try:
            query = """
                SELECT * FROM membuddy.payment_summary 
                WHERE email = ?
            """
            results = self.db.execute_query(query, (email,))
            if results and len(results) > 0:
                return results[0]
            return None
        except Exception as e:
            logger.error(f"Error getting payment summary: {e}")
            return None
    
    def close_connection(self):
        """Close database connection."""
        self.db.disconnect()

# Global database instance
db_instance = None

def get_database():
    """Get global database instance."""
    global db_instance
    if db_instance is None:
        db_instance = MembuddyDatabase()
    return db_instance

def close_database():
    """Close global database connection."""
    global db_instance
    if db_instance:
        db_instance.close_connection()
        db_instance = None 