"""
시스템 설정 테스트 스크립트
Django 환경이 올바르게 구성되었는지 확인합니다.

실행 방법:
python manage.py shell < test_setup.py
"""

import os
import sys
from datetime import datetime

print("="*60)
print("Invoice System - 설정 테스트")
print("="*60)
print(f"\n테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 1. Django 설정 확인
print("1. Django 설정 확인...")
try:
    from django.conf import settings
    print(f"   ✓ Django 버전: {__import__('django').get_version()}")
    print(f"   ✓ DEBUG 모드: {settings.DEBUG}")
    print(f"   ✓ SECRET_KEY: {'설정됨' if settings.SECRET_KEY else '설정 안됨'}")
    print(f"   ✓ ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
except Exception as e:
    print(f"   ✗ Django 설정 오류: {e}")
    sys.exit(1)

# 2. 데이터베이스 연결 확인
print("\n2. 데이터베이스 연결 확인...")
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        if result[0] == 1:
            print(f"   ✓ 데이터베이스 연결 성공")
            print(f"   ✓ DB 엔진: {settings.DATABASES['default']['ENGINE']}")
            print(f"   ✓ DB 이름: {settings.DATABASES['default']['NAME']}")
except Exception as e:
    print(f"   ✗ 데이터베이스 연결 실패: {e}")
    sys.exit(1)

# 3. 모델 확인
print("\n3. 모델 및 마이그레이션 확인...")
try:
    from core.models import CustomUser, Service, Declaration
    from django.db import models

    # 테이블 존재 확인
    user_count = CustomUser.objects.count()
    service_count = Service.objects.count()
    declaration_count = Declaration.objects.count()

    print(f"   ✓ CustomUser 모델: {user_count}개")
    print(f"   ✓ Service 모델: {service_count}개")
    print(f"   ✓ Declaration 모델: {declaration_count}개")

    if user_count == 0:
        print(f"   ⚠ 경고: 사용자가 없습니다. setup_initial_data.py를 실행하세요.")
except Exception as e:
    print(f"   ✗ 모델 로드 실패: {e}")
    print(f"   ⚠ python manage.py migrate를 실행하세요.")
    sys.exit(1)

# 4. 환경 변수 확인
print("\n4. API 키 설정 확인...")
try:
    google_creds = settings.GOOGLE_VISION_CREDENTIALS
    openai_key = settings.OPENAI_API_KEY

    if google_creds:
        if os.path.exists(google_creds):
            print(f"   ✓ Google Vision 인증 파일: 존재함")
        else:
            print(f"   ✗ Google Vision 인증 파일: 경로가 잘못되었습니다 ({google_creds})")
    else:
        print(f"   ⚠ Google Vision 인증 파일: 설정되지 않음")

    if openai_key and len(openai_key) > 20:
        print(f"   ✓ OpenAI API 키: 설정됨 (sk-...{openai_key[-8:]})")
    else:
        print(f"   ⚠ OpenAI API 키: 설정되지 않음")

except Exception as e:
    print(f"   ✗ 환경 변수 확인 실패: {e}")

# 5. 필수 패키지 확인
print("\n5. 필수 패키지 확인...")
required_packages = [
    ('django', 'Django'),
    ('rest_framework', 'Django REST Framework'),
    ('corsheaders', 'django-cors-headers'),
    ('google.cloud.vision', 'Google Cloud Vision'),
    ('openai', 'OpenAI'),
    ('PIL', 'Pillow'),
]

for package_name, display_name in required_packages:
    try:
        __import__(package_name)
        print(f"   ✓ {display_name}: 설치됨")
    except ImportError:
        print(f"   ✗ {display_name}: 설치되지 않음")

# 6. 정적 파일 및 미디어 경로 확인
print("\n6. 파일 시스템 확인...")
try:
    static_root = settings.STATIC_ROOT
    media_root = settings.MEDIA_ROOT

    print(f"   ✓ STATIC_ROOT: {static_root}")
    if not os.path.exists(static_root):
        os.makedirs(static_root, exist_ok=True)
        print(f"     → 디렉토리 생성됨")

    print(f"   ✓ MEDIA_ROOT: {media_root}")
    if not os.path.exists(media_root):
        os.makedirs(media_root, exist_ok=True)
        print(f"     → 디렉토리 생성됨")

except Exception as e:
    print(f"   ✗ 파일 시스템 확인 실패: {e}")

# 7. 관리자 계정 확인
print("\n7. 관리자 계정 확인...")
try:
    from core.models import CustomUser
    admin_users = CustomUser.objects.filter(user_type='admin')

    if admin_users.exists():
        for admin in admin_users:
            print(f"   ✓ 관리자: {admin.username}")
    else:
        print(f"   ⚠ 관리자 계정이 없습니다.")
        print(f"     → setup_initial_data.py를 실행하거나")
        print(f"     → python manage.py createsuperuser를 실행하세요.")

except Exception as e:
    print(f"   ✗ 관리자 확인 실패: {e}")

# 8. URL 패턴 확인
print("\n8. URL 패턴 확인...")
try:
    from django.urls import get_resolver
    resolver = get_resolver()

    # 주요 URL 패턴 확인
    important_urls = [
        ('login', '로그인'),
        ('dashboard', '대시보드'),
        ('service_list', '서비스 리스트'),
        ('api:process_invoice', 'API - Invoice 처리'),
    ]

    for url_name, display_name in important_urls:
        try:
            resolver.reverse(url_name)
            print(f"   ✓ {display_name}: 설정됨")
        except:
            print(f"   ⚠ {display_name}: URL 패턴을 찾을 수 없음")

except Exception as e:
    print(f"   ✗ URL 확인 실패: {e}")

# 결과 요약
print("\n" + "="*60)
print("테스트 완료!")
print("="*60)
print("\n다음 단계:")
print("1. 경고 메시지가 있다면 해당 항목을 설정하세요")
print("2. 초기 데이터가 없다면: python manage.py shell < setup_initial_data.py")
print("3. 서버 실행: python manage.py runserver")
print("4. 브라우저에서 http://localhost:8000 접속")
print("\n로그인 정보:")
print("  - 관리자: admin / P@ssw0rd")
print("  - 관세사: 6N001 / init123")
print("\n" + "="*60)
