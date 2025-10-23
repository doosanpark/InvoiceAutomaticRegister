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
    print("API 호출에 필요한 ID 정보")
    print("=" * 80)

    # 서비스 정보
    print("\n[Services]")
    cursor.execute("""
        SELECT id, name, slug
        FROM services
        ORDER BY id
    """)
    services = cursor.fetchall()
    for svc in services:
        print(f"  ID: {svc[0]}, Name: {svc[1]}, Slug: {svc[2]}")

    # ServiceUser 정보
    print("\n[ServiceUsers]")
    cursor.execute("""
        SELECT
            su.id,
            s.name as service_name,
            s.slug as service_slug,
            CASE
                WHEN su.is_default = 1 THEN 'default'
                ELSE u.customs_code
            END as customs_code,
            CASE
                WHEN su.is_default = 1 THEN '기본'
                ELSE u.customs_name
            END as customs_name
        FROM service_users su
        LEFT JOIN services s ON su.service_id = s.id
        LEFT JOIN users u ON su.user_id = u.id
        ORDER BY su.id
    """)
    service_users = cursor.fetchall()
    for su in service_users:
        print(f"  service_user_id: {su[0]} | {su[1]} ({su[2]}) - {su[4]} ({su[3]})")

    # Declaration 정보
    print("\n[Declarations]")
    cursor.execute("""
        SELECT
            d.id,
            s.name as service_name,
            s.slug as service_slug,
            d.name,
            d.code
        FROM declarations d
        LEFT JOIN services s ON d.service_id = s.id
        ORDER BY d.id
    """)
    declarations = cursor.fetchall()
    for decl in declarations:
        print(f"  declaration_id: {decl[0]} | {decl[1]} ({decl[2]}) - {decl[3]} (code: {decl[4]})")

    # 예시
    print("\n" + "=" * 80)
    print("POSTMAN API 호출 예시:")
    print("=" * 80)
    if service_users and declarations:
        su = service_users[0]
        decl = declarations[0]
        print(f"""
POST http://127.0.0.1:8000/api/process-invoice/
Headers:
  Authorization: Token f2240cd3f526f655d0d1856be4a298d7cf18ded6
  Content-Type: multipart/form-data

Body (form-data):
  service_slug: {su[2]}
  customs_code: {su[3]}
  declaration_code: {decl[4]}
  image: [파일 선택]

대응 관리페이지 URL:
  http://127.0.0.1:8000/declarations/{su[2]}/{su[3]}/{decl[4]}/

참고:
  - service_slug는 서비스의 영문 slug입니다 (예: rk-customs)
  - customs_code는 관세사부호 5자리 또는 'default'입니다 (예: 6N003)
  - declaration_code는 신고서 코드입니다 (예: CUSDEC929)
        """)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'conn' in locals():
        conn.close()
