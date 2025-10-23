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

    # slug 컬럼이 있는지 확인
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'services' AND COLUMN_NAME = 'slug'
    """)

    slug_exists = cursor.fetchone()[0] > 0

    if not slug_exists:
        print("Adding slug column to services table...")
        cursor.execute("""
            ALTER TABLE services
            ADD slug NVARCHAR(100) NULL
        """)
        print("slug column added successfully!")

        # 기존 서비스에 slug 값 생성 (name을 소문자로 변환하고 공백을 하이픈으로 변경)
        cursor.execute("SELECT id, name FROM services")
        services = cursor.fetchall()

        for service_id, service_name in services:
            # 간단한 slug 생성 (소문자 + 공백을 하이픈으로)
            slug = service_name.lower().replace(' ', '-').replace('(', '').replace(')', '')
            cursor.execute("UPDATE services SET slug = ? WHERE id = ?", (slug, service_id))
            print(f"Updated service '{service_name}' with slug '{slug}'")

        # slug를 unique로 변경
        cursor.execute("""
            ALTER TABLE services
            ALTER COLUMN slug NVARCHAR(100) NOT NULL
        """)

        cursor.execute("""
            CREATE UNIQUE INDEX IX_services_slug ON services(slug)
        """)
        print("slug column set to unique!")

    else:
        print("slug column already exists.")

    conn.commit()
    print("\nAll changes completed successfully!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'conn' in locals():
        conn.close()
