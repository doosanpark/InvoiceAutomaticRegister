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
    print("모든 서비스에 기본 설정 생성")
    print("=" * 80)

    # 모든 서비스 조회
    cursor.execute("""
        SELECT id, name, slug
        FROM services
        ORDER BY name
    """)

    services = cursor.fetchall()

    for svc in services:
        service_id = svc[0]
        service_name = svc[1]
        service_slug = svc[2]

        # 기본 설정이 있는지 확인
        cursor.execute("""
            SELECT COUNT(*)
            FROM service_users
            WHERE service_id = ? AND is_default = 1
        """, service_id)

        has_default = cursor.fetchone()[0] > 0

        if has_default:
            print(f"{service_name} ({service_slug}) - 기본 설정이 이미 존재합니다.")
        else:
            print(f"{service_name} ({service_slug}) - 기본 설정을 생성합니다...")
            cursor.execute("""
                INSERT INTO service_users (service_id, user_id, is_default, created_at)
                VALUES (?, NULL, 1, GETDATE())
            """, service_id)
            print(f"  -> 기본 설정이 생성되었습니다!")

    conn.commit()
    print("\n모든 서비스에 기본 설정이 준비되었습니다!")

    # 최종 확인
    print("\n" + "=" * 80)
    print("ServiceUser 최종 상태")
    print("=" * 80)

    cursor.execute("""
        SELECT
            su.id,
            s.name as service_name,
            su.is_default,
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

    for su in service_users:
        default_mark = " [DEFAULT]" if su[2] else ""
        print(f"ID: {su[0]} | {su[1]} | {su[3]}{default_mark}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'conn' in locals():
        conn.close()
