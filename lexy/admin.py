# lexy/admin.py
from django.contrib import admin
from .models import EmergencyRequest


@admin.register(EmergencyRequest)
class EmergencyRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'status', 'created_at']
    list_filter = ['category', 'status', 'created_at']
    search_fields = ['problem_text', 'user_phone', 'user_email']
    readonly_fields = ['created_at', 'updated_at', 'ip_address']
    fieldsets = (
        ('Основная информация', {
            'fields': ('problem_text', 'category', 'status')
        }),
        ('Контактные данные', {
            'fields': ('user_phone', 'user_email'),
            'classes': ('collapse',)
        }),
        ('Техническая информация', {
            'fields': ('ip_address', 'user_agent', 'session_key'),
            'classes': ('collapse',)
        }),
    )
