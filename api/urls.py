from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from . import views

app_name = 'api'

# 로그인 뷰를 AllowAny로 래핑
login_view = permission_classes([AllowAny])(obtain_auth_token)

urlpatterns = [
    # 인증
    path('auth/login/', login_view, name='login'),

    # 인보이스 처리
    path('process/', views.process_invoice, name='process_invoice'),

    # 처리 로그
    path('logs/', views.get_process_logs, name='get_process_logs'),
    path('logs/<int:log_id>/', views.get_process_log, name='get_process_log'),

    # 신고서 설정
    path('declaration/<int:declaration_id>/config/', views.get_declaration_config, name='get_declaration_config'),
]
