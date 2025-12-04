"""
API 요청 디버깅 미들웨어
"""
import logging

logger = logging.getLogger('api')


class RequestLoggingMiddleware:
    """모든 API 요청을 로깅하는 미들웨어"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # API 요청만 로깅
        if request.path.startswith('/api/'):
            logger.info("\n" + "="*80)
            logger.info(f"📨 [요청 수신] {request.method} {request.path}")
            logger.info("="*80)
            logger.info(f"🔑 Authorization Header: {request.META.get('HTTP_AUTHORIZATION', 'NOT PROVIDED')}")
            logger.info(f"📋 Content-Type: {request.META.get('CONTENT_TYPE', 'NOT PROVIDED')}")
            logger.info(f"👤 User: {request.user if hasattr(request, 'user') else 'Anonymous'}")
            logger.info(f"🌐 Remote Address: {request.META.get('REMOTE_ADDR')}")

            if request.GET:
                logger.info(f"📝 GET Parameters: {dict(request.GET)}")

            # POST 데이터는 view에서 로깅 (파일 제외)
            logger.info("="*80 + "\n")

        response = self.get_response(request)

        # 응답 상태 로깅
        if request.path.startswith('/api/'):
            logger.info(f"📤 [응답] {request.method} {request.path} - Status: {response.status_code}\n")

        return response
