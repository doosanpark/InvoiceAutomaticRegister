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

    # mapping_info 테이블에 컬럼이 있는지 확인
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'mapping_info' AND COLUMN_NAME = 'field_type'
    """)

    field_type_exists = cursor.fetchone()[0] > 0

    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'mapping_info' AND COLUMN_NAME = 'field_length'
    """)

    field_length_exists = cursor.fetchone()[0] > 0

    # field_type 컬럼이 없으면 추가
    if not field_type_exists:
        print("Adding field_type column...")
        cursor.execute("""
            ALTER TABLE mapping_info
            ADD field_type NVARCHAR(20) NOT NULL DEFAULT 'string'
        """)
        print("field_type column added successfully!")
    else:
        print("field_type column already exists.")

    # field_length 컬럼이 없으면 추가
    if not field_length_exists:
        print("Adding field_length column...")
        cursor.execute("""
            ALTER TABLE mapping_info
            ADD field_length INT NULL
        """)
        print("field_length column added successfully!")
    else:
        print("field_length column already exists.")

    conn.commit()
    print("\nAll columns have been added successfully!")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
