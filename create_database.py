import pyodbc
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 데이터베이스 연결 정보
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '1433')
DB_USER = os.getenv('DB_USER', 'sa')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'invoice_db')

try:
    # master 데이터베이스에 연결 (데이터베이스 생성을 위해)
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_HOST},{DB_PORT};DATABASE=master;UID={DB_USER};PWD={DB_PASSWORD}'

    print(f"SQL Server에 연결 중... (Host: {DB_HOST}:{DB_PORT})")
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()

    # 데이터베이스가 이미 존재하는지 확인
    cursor.execute(f"SELECT database_id FROM sys.databases WHERE name = '{DB_NAME}'")
    db_exists = cursor.fetchone()

    if db_exists:
        print(f"[OK] Database '{DB_NAME}' already exists.")
    else:
        # 데이터베이스 생성
        print(f"Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"[SUCCESS] Database '{DB_NAME}' created successfully!")

    cursor.close()
    conn.close()

    print("\nNext steps:")
    print("1. python manage.py migrate")
    print("2. python manage.py shell < setup_initial_data.py")
    print("3. python manage.py runserver")

except pyodbc.Error as e:
    print(f"[ERROR] {e}")
    print("\nTroubleshooting:")
    print("1. Check if SQL Server is running")
    print("2. Check if ODBC Driver 17 for SQL Server is installed")
    print("   Download: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
    print("3. Verify sa account password")
    print("4. Check if SQL Server allows TCP/IP connections")
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
