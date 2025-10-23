from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from . import views

app_name = 'api'

urlpatterns = [
    # 인증
    path('auth/login/', obtain_auth_token, name='login'),

    # 인보이스 처리
    path('process/', views.process_invoice, name='process_invoice'),

    # 처리 로그
    path('logs/', views.get_process_logs, name='get_process_logs'),
    path('logs/<int:log_id>/', views.get_process_log, name='get_process_log'),

    # 신고서 설정
    path('declaration/<int:declaration_id>/config/', views.get_declaration_config, name='get_declaration_config'),
]
