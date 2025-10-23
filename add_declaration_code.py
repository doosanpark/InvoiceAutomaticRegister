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

    # code 컬럼이 있는지 확인
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'declarations' AND COLUMN_NAME = 'code'
    """)

    code_exists = cursor.fetchone()[0] > 0

    if not code_exists:
        print("Adding code column to declarations table...")
        cursor.execute("""
            ALTER TABLE declarations
            ADD code NVARCHAR(50) NULL
        """)
        print("code column added successfully!")
    else:
        print("code column already exists.")

    conn.commit()
    print("\nAll changes completed successfully!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'conn' in locals():
        conn.close()
