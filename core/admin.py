from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Service, ServiceUser, Declaration,
    TableProcessConfig, MappingInfo, PromptConfig, InvoiceProcessLog
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'user_type', 'customs_code', 'customs_name', 'is_first_login', 'is_active']
    list_filter = ['user_type', 'is_active', 'is_first_login']
    search_fields = ['username', 'customs_code', 'customs_name']

    fieldsets = UserAdmin.fieldsets + (
        ('추가 정보', {
            'fields': ('user_type', 'customs_code', 'customs_name', 'is_first_login')
        }),
    )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


@admin.register(ServiceUser)
class ServiceUserAdmin(admin.ModelAdmin):
    list_display = ['service', 'user', 'is_default', 'created_at']
    list_filter = ['service', 'is_default']
    search_fields = ['service__name', 'user__customs_name', 'user__customs_code']


@admin.register(Declaration)
class DeclarationAdmin(admin.ModelAdmin):
    list_display = ['name', 'service', 'declaration_type', 'is_active', 'created_at']
    list_filter = ['service', 'declaration_type', 'is_active']
    search_fields = ['name', 'description']


@admin.register(TableProcessConfig)
class TableProcessConfigAdmin(admin.ModelAdmin):
    list_display = ['declaration', 'work_group', 'db_table_name', 'process_order',
                   'service_user', 'is_active']
    list_filter = ['declaration', 'is_active']
    search_fields = ['work_group', 'db_table_name']
    ordering = ['declaration', 'process_order']

    def get_fields(self, request, obj=None):
        """권한에 따라 필드 표시"""
        if request.user.is_superuser or request.user.user_type == 'admin':
            # admin은 모든 필드 표시
            return ['declaration', 'service_user', 'work_group', 'db_table_name',
                   'process_order', 'is_active']
        else:
            # 일반 사용자는 업무그룹만 표시
            return ['declaration', 'service_user', 'work_group', 'is_active']

    def get_readonly_fields(self, request, obj=None):
        """권한에 따라 읽기 전용 필드 설정"""
        if request.user.is_superuser or request.user.user_type == 'admin':
            return []
        else:
            # 일반 사용자는 모두 읽기 전용
            return ['declaration', 'service_user', 'work_group', 'is_active']

    def get_list_display(self, request):
        """권한에 따라 리스트 컬럼 표시"""
        if request.user.is_superuser or request.user.user_type == 'admin':
            return ['declaration', 'work_group', 'db_table_name', 'process_order',
                   'service_user', 'is_active']
        else:
            return ['declaration', 'work_group', 'service_user', 'is_active']


@admin.register(MappingInfo)
class MappingInfoAdmin(admin.ModelAdmin):
    list_display = ['unipass_field_name', 'db_table_name', 'db_field_name',
                   'declaration', 'table_config', 'priority', 'is_active']
    list_filter = ['declaration', 'table_config', 'is_active']
    search_fields = ['unipass_field_name', 'db_table_name', 'db_field_name']

    def get_fields(self, request, obj=None):
        """권한에 따라 필드 표시"""
        if request.user.is_superuser or request.user.user_type == 'admin':
            return ['declaration', 'service_user', 'table_config', 'unipass_field_name',
                   'db_table_name', 'db_field_name', 'field_type', 'field_length',
                   'priority', 'is_active']
        else:
            return ['declaration', 'service_user', 'table_config', 'unipass_field_name',
                   'field_type', 'field_length', 'priority', 'is_active']


@admin.register(PromptConfig)
class PromptConfigAdmin(admin.ModelAdmin):
    list_display = ['mapping', 'prompt_type', 'service_user', 'created_by', 'created_at']
    list_filter = ['prompt_type', 'is_active']
    search_fields = ['prompt_text', 'mapping__unipass_field_name']


@admin.register(InvoiceProcessLog)
class InvoiceProcessLogAdmin(admin.ModelAdmin):
    list_display = ['declaration', 'service_user', 'status', 'processing_time', 'created_at']
    list_filter = ['status', 'declaration', 'created_at']
    search_fields = ['ocr_text', 'error_message']
    readonly_fields = ['created_at', 'completed_at', 'processing_time']
