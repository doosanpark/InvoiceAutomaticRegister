"""
커스텀 인증 클래스
Bearer Token 지원
"""
from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    """
    Bearer Token 형식 지원
    Authorization: Bearer <token>
    """
    keyword = 'Bearer'
