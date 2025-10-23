"""
현재 admin 사용자 정보 확인
실행: python manage.py shell < check_user.py
"""

from core.models import CustomUser

admin = CustomUser.objects.filter(username='admin').first()

if admin:
    print("=" * 50)
    print("Admin 사용자 정보")
    print("=" * 50)
    print(f"Username: {admin.username}")
    print(f"User Type: {admin.user_type}")
    print(f"Is Staff: {admin.is_staff}")
    print(f"Is Superuser: {admin.is_superuser}")
    print(f"Is Active: {admin.is_active}")
    print(f"Is First Login: {admin.is_first_login}")
    print("=" * 50)

    # user_type이 'admin'이 아니면 수정
    if admin.user_type != 'admin':
        print("\n⚠ user_type이 'admin'이 아닙니다!")
        print("수정하시겠습니까? (y/n)")
        admin.user_type = 'admin'
        admin.save()
        print("✓ user_type을 'admin'으로 변경했습니다.")
else:
    print("admin 사용자를 찾을 수 없습니다!")
