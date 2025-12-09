from django.urls import path
from . import views

urlpatterns = [
    # 인증
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password_view, name='change_password'),

    # 대시보드
    path('dashboard/', views.dashboard, name='dashboard'),

    # 서비스 (관리자)
    path('services/', views.service_list_view, name='service_list'),
    path('services/add/', views.service_add_view, name='service_add'),
    path('services/<slug:service_slug>/', views.service_detail_view, name='service_detail'),
    path('services/<slug:service_slug>/add-customs/', views.add_customs_to_service, name='add_customs_to_service'),

    # 신고서
    path('declarations/', views.declaration_list_view, name='declaration_list'),
    path('declarations/<slug:service_slug>/<str:customs_code>/', views.declaration_list_view, name='declaration_list_with_user'),

    # 신고서 관리 (더 구체적인 패턴을 먼저 배치)
    path('declarations/<slug:service_slug>/<str:customs_code>/add/', views.declaration_add_view, name='declaration_add'),
    path('declarations/<slug:service_slug>/<str:customs_code>/<str:declaration_code>/edit/', views.declaration_edit_view, name='declaration_edit'),
    path('declarations/<slug:service_slug>/<str:customs_code>/<str:declaration_code>/delete/', views.declaration_delete_view, name='declaration_delete'),

    # 신고서 상세
    path('declarations/<slug:service_slug>/<str:customs_code>/<str:declaration_code>/', views.declaration_detail_view, name='declaration_detail'),

    # AJAX
    path('api/prompt/<int:mapping_id>/update/', views.update_prompt_view, name='update_prompt'),
    path('api/mapping/<int:declaration_id>/add/', views.add_mapping_view, name='add_mapping'),
    path('api/mapping/<int:mapping_id>/update/', views.update_mapping_view, name='update_mapping'),
    path('api/mapping/<int:mapping_id>/delete/', views.delete_mapping_view, name='delete_mapping'),
    path('api/declaration/<int:declaration_id>/metadata/', views.update_metadata_view, name='update_metadata'),
    path('api/declaration/<int:declaration_id>/specification/upload/', views.upload_specification_view, name='upload_specification'),
    path('api/declaration/<int:declaration_id>/specification/download/', views.download_specification_view, name='download_specification'),
    
    # 테이블 처리 설정 API
    path('api/table-config/<int:declaration_id>/add/', views.add_table_config_view, name='add_table_config'),
    path('api/table-config/<int:config_id>/update/', views.update_table_config_view, name='update_table_config'),
    path('api/table-config/<int:config_id>/delete/', views.delete_table_config_view, name='delete_table_config'),
]
