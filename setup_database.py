#!/usr/bin/env python3
"""
Database Setup Script for Membuddy Application
Microsoft SQL Server Version

This script sets up the database connection and tests the configuration.
"""

import os
import sys
from dotenv import load_dotenv
import pyodbc
import pymssql

def test_connection():
    """Test database connection using both pyodbc and pymssql."""
    load_dotenv()
    
    # Configuration
    config = {
        'server': os.getenv('DB_HOST', 'et-ci-dev-etintl-dbsrv.database.windows.net'),
        'database': os.getenv('DB_NAME', 'et-ci-dev-etintl-sqldb'),
        'user': os.getenv('DB_USER', 'MosinInamdar'),
        'password': os.getenv('DB_PASSWORD', 'Mosin@1823!'),
        'port': int(os.getenv('DB_PORT', 1433))
    }
    
    print("Testing database connection...")
    print(f"Server: {config['server']}")
    print(f"Database: {config['database']}")
    print(f"User: {config['user']}")
    print(f"Port: {config['port']}")
    print("-" * 50)
    
    # Test pyodbc connection
    print("Testing pyodbc connection...")
    try:
        connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={config['server']};DATABASE={config['database']};UID={config['user']};PWD={config['password']};TrustServerCertificate=yes;"
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"✓ pyodbc connection successful!")
        print(f"SQL Server Version: {version}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"✗ pyodbc connection failed: {e}")
        
        # Test pymssql connection
        print("\nTesting pymssql connection...")
        try:
            conn = pymssql.connect(
                server=config['server'],
                database=config['database'],
                user=config['user'],
                password=config['password'],
                port=config['port']
            )
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            print(f"✓ pymssql connection successful!")
            print(f"SQL Server Version: {version}")
            cursor.close()
            conn.close()
            return True
        except Exception as e2:
            print(f"✗ pymssql connection failed: {e2}")
            return False

def check_tables():
    """Check if the required tables exist."""
    print("\nChecking for required tables...")
    
    try:
        # Try pyodbc first
        connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={os.getenv('DB_HOST')};DATABASE={os.getenv('DB_NAME')};UID={os.getenv('DB_USER')};PWD={os.getenv('DB_PASSWORD')};TrustServerCertificate=yes;"
        conn = pyodbc.connect(connection_string)
    except:
        # Fallback to pymssql
        conn = pymssql.connect(
            server=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=int(os.getenv('DB_PORT', 1433))
        )
    
    cursor = conn.cursor()
    
    # Check for required tables with membuddy schema naming convention
    required_tables = [
        'membuddy.master_table',
        'membuddy.user_data',
        'membuddy.membership_details',
        'membuddy.payments',
        'membuddy.feedback'
    ]
    
    for table in required_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✓ {table}: {count} records")
        except Exception as e:
            print(f"✗ {table}: Not found or error - {e}")
    
    cursor.close()
    conn.close()

def main():
    """Main setup function."""
    print("=" * 60)
    print("Membuddy Database Setup - Microsoft SQL Server")
    print("=" * 60)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Warning: .env file not found. Using default configuration.")
        print("Please create a .env file with your database credentials.")
        print("See env_example.txt for reference.")
        print()
    
    # Test connection
    if test_connection():
        print("\n✓ Database connection successful!")
        
        # Check tables
        check_tables()
        
        print("\n" + "=" * 60)
        print("Setup completed successfully!")
        print("Next steps:")
        print("1. Run the SQL script in SQL Server Management Studio")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Test the application: python test_database.py")
        print("4. Run the Streamlit app: streamlit run streamlit_app/app.py")
        print("=" * 60)
    else:
        print("\n✗ Database connection failed!")
        print("Please check your configuration and try again.")
        print("Make sure:")
        print("- Your SQL Server is running and accessible")
        print("- Your credentials are correct")
        print("- Your firewall allows connections on port 1433")
        print("- You have the required ODBC drivers installed")
        sys.exit(1)

if __name__ == "__main__":
    main() 