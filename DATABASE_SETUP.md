# Membuddy Database Setup Guide
## Microsoft SQL Server (MSSQL) Version

This guide will help you set up the Membuddy application with Microsoft SQL Server.

## Prerequisites

1. **Microsoft SQL Server** - You're using Azure SQL Database at `et-ci-dev-etintl-dbsrv.database.windows.net`
2. **SQL Server Management Studio (SSMS)** - For running SQL scripts
3. **Python 3.8+** - For running the application
4. **ODBC Driver 17 for SQL Server** - For database connectivity

## Database Configuration

### 1. Database Details
- **Server**: `et-ci-dev-etintl-dbsrv.database.windows.net`
- **Database**: `et-ci-dev-etintl-sqldb`
- **Username**: `MosinInamdar`
- **Password**: `Mosin@1823!`
- **Port**: `1433` (default SQL Server port)

### 2. Environment Variables
Create a `.env` file in the project root with the following configuration:

```env
# Database Configuration for Microsoft SQL Server
DB_HOST=et-ci-dev-etintl-dbsrv.database.windows.net
DB_NAME=et-ci-dev-etintl-sqldb
DB_USER=MosinInamdar
DB_PASSWORD=Mosin@1823!
DB_PORT=1433

# LangChain Configuration
GROQ_API_KEY=your_groq_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langchain_api_key_here

# Application Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
```

## Database Setup Steps

### Step 1: Run the SQL Script

1. **Open SQL Server Management Studio (SSMS)**
2. **Connect to your database server**:
   - Server name: `et-ci-dev-etintl-dbsrv.database.windows.net`
   - Authentication: SQL Server Authentication
   - Login: `MosinInamdar`
   - Password: `Mosin@1823!`

3. **Run the database setup script**:
   - Open the `database_setup.sql` file in SSMS
   - Execute the entire script (F5 or Ctrl+E)
   - The script will create:
     - Schemas: `elevate` and `membuddy`
     - Tables with the naming convention: `elevate.membuddy.tablename`
     - Sample data for testing
     - Views for common queries
     - Stored procedures for operations

### Step 2: Verify Database Setup

After running the script, you should see:
- 5 tables created with sample data
- 3 views for common queries
- 4 stored procedures for operations

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

The requirements include:
- `pyodbc==4.0.39` - Primary SQL Server connector
- `pymssql==2.2.8` - Fallback SQL Server connector
- Other application dependencies

### Step 4: Test the Database Connection

```bash
python setup_database.py
```

This will:
- Test the database connection using both pyodbc and pymssql
- Verify that all required tables exist
- Show sample data counts

### Step 5: Run Comprehensive Tests

```bash
python test_database.py
```

This will test:
- Database connection
- Member operations
- Payment operations
- Feedback operations
- Database views

## Database Schema

### Tables Created

1. **`elevate.membuddy.master_table`** - Main member information
   - `member_id` (Primary Key)
   - `full_name`, `email`, `address`
   - `graduation_year`, `membership_type`
   - `join_date`, `expiration_date`, `status`

2. **`elevate.membuddy.user_data`** - Additional user information
   - `id` (Primary Key)
   - `member_id` (Foreign Key)
   - `phone`, `company`, `job_title`, `department`
   - `emergency_contact`, `emergency_phone`

3. **`elevate.membuddy.membership_details`** - Membership specifics
   - `id` (Primary Key)
   - `member_id` (Foreign Key)
   - `membership_level`, `benefits`, `renewal_cycle`
   - `auto_renewal`, `renewal_amount`, `discount_percentage`

4. **`elevate.membuddy.payments`** - Payment transactions
   - `id` (Primary Key)
   - `member_id` (Foreign Key)
   - `payment_method`, `amount`, `currency`
   - `transaction_id`, `payment_status`, `payment_date`

5. **`elevate.membuddy.feedback`** - User feedback
   - `id` (Primary Key)
   - `member_id` (Foreign Key, nullable)
   - `email`, `rating`, `comment`
   - `feedback_type`, `status`

### Views Created

1. **`elevate.membuddy.active_members`** - All active members with details
2. **`elevate.membuddy.expiring_memberships`** - Memberships expiring within 30 days
3. **`elevate.membuddy.payment_summary`** - Payment summaries by member

### Stored Procedures Created

1. **`elevate.membuddy.GetMemberProfile`** - Get complete member profile
2. **`elevate.membuddy.GetRenewalOptions`** - Get renewal options for a member
3. **`elevate.membuddy.ProcessPayment`** - Process a payment transaction
4. **`elevate.membuddy.CollectFeedback`** - Collect user feedback

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify server name and credentials
   - Check firewall settings (port 1433)
   - Ensure ODBC Driver 17 is installed

2. **ODBC Driver Not Found**
   - Download and install "ODBC Driver 17 for SQL Server"
   - Available from Microsoft's website

3. **Authentication Failed**
   - Verify username and password
   - Check if the user has access to the database

4. **Tables Not Found**
   - Ensure the SQL script was executed completely
   - Check for any error messages during script execution

### Testing Connection

You can test the connection manually:

```python
import pyodbc
connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=et-ci-dev-etintl-dbsrv.database.windows.net;DATABASE=et-ci-dev-etintl-sqldb;UID=MosinInamdar;PWD=Mosin@1823!;TrustServerCertificate=yes;"
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()
cursor.execute("SELECT @@VERSION")
version = cursor.fetchone()[0]
print(f"SQL Server Version: {version}")
conn.close()
```

## Next Steps

After successful database setup:

1. **Test the application**: `python test_database.py`
2. **Run the Streamlit app**: `streamlit run streamlit_app/app.py`
3. **Access the application** at `http://localhost:8501`

## Migration from Excel

The application has been migrated from Excel files to Microsoft SQL Server:

- **Benefits**: Better performance, data integrity, concurrent access
- **Data**: Sample data is included in the setup script
- **Tools**: All tools have been updated to use the database
- **Backup**: Regular database backups recommended

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review error messages in the console
3. Verify database connectivity
4. Ensure all dependencies are installed 