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
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    print("=" * 80)
    print("ServiceUser 확인")
    print("=" * 80)

    cursor.execute("""
        SELECT
            su.id,
            s.name as service_name,
            s.slug as service_slug,
            su.is_default,
            CASE
                WHEN su.user_id IS NULL THEN 'NULL'
                ELSE CAST(su.user_id as NVARCHAR)
            END as user_id,
            CASE
                WHEN su.user_id IS NULL THEN '기본'
                ELSE u.customs_name
            END as customs_name
        FROM service_users su
        LEFT JOIN services s ON su.service_id = s.id
        LEFT JOIN users u ON su.user_id = u.id
        ORDER BY s.name, su.is_default DESC
    """)

    service_users = cursor.fetchall()

    if service_users:
        for su in service_users:
            default_mark = " [DEFAULT]" if su[3] else ""
            print(f"ID: {su[0]} | {su[1]} ({su[2]}) | {su[5]} | is_default: {su[3]}{default_mark}")
    else:
        print("ServiceUser가 없습니다!")

    # 각 서비스별로 기본 설정이 있는지 확인
    print("\n" + "=" * 80)
    print("서비스별 기본 설정 확인")
    print("=" * 80)

    cursor.execute("""
        SELECT
            s.id,
            s.name,
            s.slug,
            (SELECT COUNT(*) FROM service_users WHERE service_id = s.id AND is_default = 1) as has_default
        FROM services s
        ORDER BY s.name
    """)

    services = cursor.fetchall()

    for svc in services:
        has_default = "O" if svc[3] > 0 else "X"
        print(f"{svc[1]} ({svc[2]}) - 기본 설정: {has_default}")

        if svc[3] == 0:
            print(f"  -> {svc[1]}에 기본 설정이 없습니다! 생성하시겠습니까?")
            create = input("  생성하려면 'y' 입력: ")
            if create.lower() == 'y':
                cursor.execute("""
                    INSERT INTO service_users (service_id, user_id, is_default, created_at)
                    VALUES (?, NULL, 1, GETDATE())
                """, svc[0])
                conn.commit()
                print(f"  -> {svc[1]}에 기본 설정이 생성되었습니다!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'conn' in locals():
        conn.close()
