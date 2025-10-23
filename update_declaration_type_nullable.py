import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

# DB 연결 정보
server = os.getenv('DB_HOST', 'localhost')
database = os.getenv('DB_NAME', 'invoice_db')
username = os.getenv('DB_USER', 'sa')
password = os.getenv('DB_PASSWORD', 'fpelchlrh')

# 연결 문자열
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

try:
    # DB 연결
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    print("1. Checking CHECK constraint on declaration_type...")
    cursor.execute("""
        SELECT CONSTRAINT_NAME
        FROM INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE
        WHERE TABLE_NAME = 'declarations' AND COLUMN_NAME = 'declaration_type'
        AND CONSTRAINT_NAME LIKE 'CK_%'
    """)

    constraints = cursor.fetchall()

    if constraints:
        print(f"Found {len(constraints)} CHECK constraint(s):")
        for constraint in constraints:
            constraint_name = constraint[0]
            print(f"  Dropping constraint: {constraint_name}")
            cursor.execute(f"ALTER TABLE declarations DROP CONSTRAINT {constraint_name}")
    else:
        print("No CHECK constraints found on declaration_type")

    print("\n2. Making declaration_type nullable...")
    cursor.execute("""
        ALTER TABLE declarations
        ALTER COLUMN declaration_type NVARCHAR(20) NULL
    """)
    print("declaration_type column is now nullable")

    conn.commit()
    print("\nAll changes completed successfully!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'conn' in locals():
        conn.close()
