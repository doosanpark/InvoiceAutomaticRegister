import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_system.settings')
django.setup()

from core.models import CustomUser
from rest_framework.authtoken.models import Token

# 사용자 선택
print("Available users:")
print("  1. admin")
print("  2. 6N001 (A customs broker)")
print("  3. 6N002 (Woori customs broker)")

username = input("\nEnter username (or number): ").strip()

# 숫자로 입력한 경우
user_map = {
    '1': 'admin',
    '2': '6N001',
    '3': '6N002'
}

if username in user_map:
    username = user_map[username]

try:
    user = CustomUser.objects.get(username=username)

    # 기존 토큰 삭제 및 새로 생성
    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)

    print(f"\n{'='*60}")
    print(f"Token created for: {user.username}")
    print(f"{'='*60}")
    print(f"\nToken: {token.key}")
    print(f"\nUse in Postman:")
    print(f"Authorization: Token {token.key}")
    print(f"{'='*60}\n")

except CustomUser.DoesNotExist:
    print(f"Error: User '{username}' not found")
