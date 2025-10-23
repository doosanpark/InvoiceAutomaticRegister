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

    # core.0001_initial 마이그레이션 기록 추가
    print("Adding core.0001_initial migration record...")
    cursor.execute("""
        IF NOT EXISTS (SELECT 1 FROM django_migrations WHERE app = 'core' AND name = '0001_initial')
        BEGIN
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('core', '0001_initial', GETDATE())
        END
        ELSE
        BEGIN
            PRINT 'core.0001_initial already exists'
        END
    """)

    conn.commit()
    print("Migration history fixed!")

    # authtoken 테이블이 있는지 확인
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = 'authtoken_token'
    """)

    token_table_exists = cursor.fetchone()[0] > 0

    if not token_table_exists:
        print("\nCreating authtoken_token table...")
        cursor.execute("""
            CREATE TABLE authtoken_token (
                [key] NVARCHAR(40) NOT NULL PRIMARY KEY,
                created DATETIME2(6) NOT NULL,
                user_id BIGINT NOT NULL UNIQUE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('authtoken', '0001_initial', GETDATE())
        """)

        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('authtoken', '0002_auto_20160226_1747', GETDATE())
        """)

        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('authtoken', '0003_tokenproxy', GETDATE())
        """)

        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('authtoken', '0004_alter_tokenproxy_options', GETDATE())
        """)

        conn.commit()
        print("authtoken_token table created successfully!")
    else:
        print("\nauthtoken_token table already exists.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'conn' in locals():
        conn.close()
