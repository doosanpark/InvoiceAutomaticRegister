"""
관리자 계정 생성 스크립트
실행 방법: python manage.py shell < create_admin.py
"""

from core.models import CustomUser

# 기존 admin 계정 삭제 (있다면)
CustomUser.objects.filter(username='admin').delete()

# 새 관리자 계정 생성
admin = CustomUser.objects.create_user(
    username='admin',
    password='P@ssw0rd',
    user_type='admin',
    is_staff=True,
    is_superuser=True,
    is_first_login=False
)

print(f"✓ 관리자 계정 생성 완료!")
print(f"  Username: admin")
print(f"  Password: P@ssw0rd")
print(f"  User Type: {admin.user_type}")
print(f"  Is Staff: {admin.is_staff}")
print(f"  Is Superuser: {admin.is_superuser}")
