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
    # master 데이터베이스에 연결
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_HOST},{DB_PORT};DATABASE=master;UID={DB_USER};PWD={DB_PASSWORD}'

    print(f"Connecting to SQL Server... (Host: {DB_HOST}:{DB_PORT})")
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()

    # 데이터베이스 삭제
    print(f"Dropping database '{DB_NAME}'...")
    cursor.execute(f"IF EXISTS (SELECT name FROM sys.databases WHERE name = '{DB_NAME}') DROP DATABASE {DB_NAME}")
    print(f"[OK] Database '{DB_NAME}' dropped")

    # 데이터베이스 생성
    print(f"Creating database '{DB_NAME}'...")
    cursor.execute(f"CREATE DATABASE {DB_NAME}")
    print(f"[SUCCESS] Database '{DB_NAME}' created successfully!")

    cursor.close()
    conn.close()

    print("\nNext steps:")
    print("1. python manage.py migrate")
    print("2. python run_setup.py")
    print("3. python manage.py runserver")

except pyodbc.Error as e:
    print(f"[ERROR] {e}")
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
