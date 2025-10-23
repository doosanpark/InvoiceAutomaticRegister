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

    print("1. Checking for NULL or empty code values...")
    cursor.execute("""
        SELECT id, name, code
        FROM declarations
        WHERE code IS NULL OR code = ''
    """)

    null_records = cursor.fetchall()

    if null_records:
        print(f"\nFound {len(null_records)} records with NULL or empty code:")
        for record in null_records:
            print(f"  ID: {record[0]}, Name: {record[1]}, Code: {record[2]}")

        print("\n2. Updating NULL/empty codes with default values...")
        for record in null_records:
            record_id = record[0]
            record_name = record[1]
            # Generate code from name or use ID
            default_code = record_name.upper().replace(' ', '_') if record_name else f'DECL_{record_id}'

            cursor.execute("""
                UPDATE declarations
                SET code = ?
                WHERE id = ?
            """, default_code, record_id)
            print(f"  Updated ID {record_id}: code = '{default_code}'")
    else:
        print("No NULL or empty code values found.")

    print("\n3. Making code field NOT NULL and UNIQUE...")

    # Check if code is already NOT NULL
    cursor.execute("""
        SELECT IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'declarations' AND COLUMN_NAME = 'code'
    """)

    is_nullable = cursor.fetchone()[0]

    if is_nullable == 'YES':
        print("Altering code column to NOT NULL...")
        cursor.execute("""
            ALTER TABLE declarations
            ALTER COLUMN code NVARCHAR(50) NOT NULL
        """)
        print("Code column is now NOT NULL")
    else:
        print("Code column is already NOT NULL")

    # Check if unique constraint exists
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
        WHERE TABLE_NAME = 'declarations'
        AND CONSTRAINT_TYPE = 'UNIQUE'
        AND CONSTRAINT_NAME LIKE '%code%'
    """)

    unique_exists = cursor.fetchone()[0] > 0

    if not unique_exists:
        print("Adding UNIQUE constraint on code column...")
        cursor.execute("""
            ALTER TABLE declarations
            ADD CONSTRAINT UQ_declarations_code UNIQUE (code)
        """)
        print("UNIQUE constraint added on code column")
    else:
        print("UNIQUE constraint already exists on code column")

    conn.commit()
    print("\nAll changes completed successfully!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'conn' in locals():
        conn.close()
