import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

# admin 사용자 찾기
try:
    admin_user = User.objects.get(username='admin')

    # 기존 토큰 삭제 후 재생성
    Token.objects.filter(user=admin_user).delete()
    token = Token.objects.create(user=admin_user)

    print(f"Admin 사용자의 토큰이 생성되었습니다:")
    print(f"Token: {token.key}")
    print(f"\nPostman에서 사용:")
    print(f"Authorization: Token {token.key}")

except User.DoesNotExist:
    print("admin 사용자를 찾을 수 없습니다.")
    print("\n사용 가능한 사용자 목록:")
    for user in User.objects.all():
        print(f"  - {user.username}")
