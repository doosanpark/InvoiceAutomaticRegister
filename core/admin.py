from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Service, ServiceUser, Declaration,
    MappingInfo, PromptConfig, InvoiceProcessLog
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


@admin.register(MappingInfo)
class MappingInfoAdmin(admin.ModelAdmin):
    list_display = ['unipass_field_name', 'db_table_name', 'db_field_name',
                   'declaration', 'priority', 'is_active']
    list_filter = ['declaration', 'is_active']
    search_fields = ['unipass_field_name', 'db_table_name', 'db_field_name']


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
