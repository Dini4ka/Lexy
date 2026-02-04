# lexy/admin.py
from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.utils import timezone
from django.db.models import Count, Avg
from .models import EmergencyRequest, Lawyer, LawyerChat, ChatMessage, Consultation, LawyerReview


@admin.register(EmergencyRequest)
class EmergencyRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_problem', 'status', 'urgency', 'category', 'created_at', 'chat_link')
    list_filter = ('status', 'urgency', 'category', 'created_at')
    search_fields = ('problem_text', 'summary', 'error_message')
    readonly_fields = ('created_at', 'analyzed_at', 'get_analysis_duration', 'chats_count')

    fieldsets = (
        ('Основная информация', {
            'fields': ('problem_text', 'status', 'category', 'urgency', 'confidence')
        }),
        ('Ответ ИИ', {
            'fields': ('ai_response', 'response_format', 'summary')
        }),
        ('Связанные чаты', {
            'fields': ('chats_count',),
            'classes': ('collapse',)
        }),
        ('Метаданные', {
            'fields': ('ip_address', 'user_agent', 'session_key')
        }),
        ('Даты', {
            'fields': ('created_at', 'analyzed_at', 'get_analysis_duration')
        }),
        ('Ошибки', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

    def short_problem(self, obj):
        """Краткое описание проблемы для списка"""
        if len(obj.problem_text) > 100:
            return obj.problem_text[:100] + '...'
        return obj.problem_text

    short_problem.short_description = 'Проблема'

    def get_analysis_duration(self, obj):
        """Длительность анализа для отображения в админке"""
        duration = obj.analysis_duration
        if duration:
            seconds = duration.total_seconds()
            if seconds < 60:
                return f"{int(seconds)} сек"
            elif seconds < 3600:
                return f"{int(seconds / 60)} мин"
            else:
                return f"{int(seconds / 3600)} ч"
        return '-'

    get_analysis_duration.short_description = 'Длительность анализа'

    def chats_count(self, obj):
        """Количество связанных чатов"""
        return obj.chats.count()

    chats_count.short_description = 'Количество чатов'

    def chat_link(self, obj):
        """Ссылка на чаты"""
        count = obj.chats.count()
        if count > 0:
            return format_html(
                '<a href="{}?request__id__exact={}">{} чат(ов)</a>',
                '/admin/lexy/lawyerchat/',
                obj.id,
                count
            )
        return '-'

    chat_link.short_description = 'Чаты'


@admin.register(Lawyer)
class LawyerAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization_display', 'experience_years', 'rating_display',
                    'cases_completed', 'is_available', 'response_time', 'photo_preview')
    list_filter = ('specialization', 'is_available', 'is_verified', 'is_premium', 'created_at')
    search_fields = ('name', 'bio', 'education', 'certifications', 'personality')
    list_editable = ('is_available', 'response_time')
    readonly_fields = ('created_at', 'updated_at', 'stats_summary', 'photo_preview_large')

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'specialization', 'photo', 'photo_preview_large')
        }),
        ('Профессиональные данные', {
            'fields': ('experience', 'rating', 'cases_completed', 'success_rate', 'response_time', 'availability')
        }),
        ('Описание и образование', {
            'fields': ('bio', 'education', 'certifications'),
            'classes': ('collapse',)
        }),
        ('AI Конфигурация', {
            'fields': ('assistant_id', 'model_uri', 'system_name', 'personality', 'demo_messages', 'tags'),
            'classes': ('collapse',)
        }),
        ('Статусы и цены', {
            'fields': ('is_available', 'is_verified', 'is_premium', 'price')
        }),
        ('Статистика', {
            'fields': ('stats_summary', 'average_response_time_minutes', 'client_satisfaction'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['make_available', 'make_unavailable', 'verify_lawyers']

    def specialization_display(self, obj):
        """Отображаемое название специализации"""
        return obj.get_specialization_display()

    specialization_display.short_description = 'Специализация'

    def experience_years(self, obj):
        """Опыт работы в годах"""
        return f"{obj.experience} лет"

    experience_years.short_description = 'Опыт'

    def rating_display(self, obj):
        """Форматированный рейтинг"""
        return f"{obj.rating:.1f}"

    rating_display.short_description = 'Рейтинг'

    def photo_preview(self, obj):
        """Маленькое превью фото"""
        if obj.photo:
            return format_html(f'<img src="{obj.photo.url}" style="max-height: 30px; border-radius: 50%;" />')
        return "📷"

    photo_preview.short_description = 'Фото'

    def photo_preview_large(self, obj):
        """Большое превью фото"""
        if obj.photo:
            return format_html(f'<img src="{obj.photo.url}" style="max-height: 200px; max-width: 200px;" />')
        return "Фото не загружено"

    photo_preview_large.short_description = 'Превью фото'

    def stats_summary(self, obj):
        """Сводка статистики"""
        active_chats = obj.chats.filter(status='active').count()
        completed_chats = obj.chats.filter(status='completed').count()
        reviews = obj.reviews.count()

        return format_html(
            '''
            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                <strong>Активных чатов:</strong> {}<br>
                <strong>Завершенных консультаций:</strong> {}<br>
                <strong>Отзывов:</strong> {}<br>
                <strong>AI-агент:</strong> {}
            </div>
            ''',
            active_chats,
            completed_chats,
            reviews,
            "✅" if obj.assistant_id else "❌"
        )

    stats_summary.short_description = 'Статистика'

    def make_available(self, request, queryset):
        """Сделать выбранных юристов доступными"""
        queryset.update(is_available=True)
        self.message_user(request, f"{queryset.count()} юристов стали доступны")

    make_available.short_description = "Сделать доступными"

    def make_unavailable(self, request, queryset):
        """Сделать выбранных юристов недоступными"""
        queryset.update(is_available=False)
        self.message_user(request, f"{queryset.count()} юристов стали недоступны")

    make_unavailable.short_description = "Сделать недоступными"

    def verify_lawyers(self, request, queryset):
        """Верифицировать выбранных юристов"""
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} юристов верифицированы")

    verify_lawyers.short_description = "Верифицировать"


class ChatMessageInline(admin.TabularInline):
    """Inline для сообщений в админке чатов"""
    model = ChatMessage
    extra = 0
    readonly_fields = ('timestamp', 'sender', 'short_message', 'is_read')
    fields = ('timestamp', 'sender', 'short_message', 'is_read')
    ordering = ('-timestamp',)

    def short_message(self, obj):
        """Краткое сообщение"""
        if len(obj.message) > 50:
            return obj.message[:50] + '...'
        return obj.message

    short_message.short_description = 'Сообщение'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LawyerChat)
class LawyerChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_client', 'lawyer_link', 'status', 'message_count',
                    'last_message_at', 'duration_display', 'created_at')
    list_filter = ('status', 'lawyer', 'created_at', 'is_anonymous')
    search_fields = ('request__problem_text', 'lawyer__name', 'client_name', 'client_email')
    readonly_fields = ('created_at', 'updated_at', 'archived_at', 'duration_display',
                       'messages_preview', 'get_client_full')
    inlines = [ChatMessageInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('request', 'lawyer', 'status', 'title')
        }),
        ('Информация о клиенте', {
            'fields': ('get_client_full', 'client_name', 'client_email', 'is_anonymous')
        }),
        ('Статистика', {
            'fields': ('message_count', 'last_message_at', 'duration_display')
        }),
        ('Превью сообщений', {
            'fields': ('messages_preview',),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'archived_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_completed', 'mark_as_archived', 'export_chats']

    def get_client(self, obj):
        """Клиент для отображения в списке"""
        if obj.client_name:
            return obj.client_name
        return f"Запрос #{obj.request.id}"

    get_client.short_description = 'Клиент'

    def get_client_full(self, obj):
        """Полная информация о клиенте"""
        return format_html(
            '''
            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                <strong>ID запроса:</strong> {}<br>
                <strong>Проблема:</strong> {}<br>
                <strong>Категория:</strong> {}<br>
                <strong>Создан:</strong> {}
            </div>
            ''',
            obj.request.id,
            obj.request.problem_text[:100] + '...' if len(obj.request.problem_text) > 100 else obj.request.problem_text,
            obj.request.get_category_display() if obj.request.category else 'Не указана',
            obj.request.created_at.strftime('%d.%m.%Y %H:%M')
        )

    get_client_full.short_description = 'Информация о запросе'

    def lawyer_link(self, obj):
        """Ссылка на юриста"""
        return format_html(
            '<a href="{}">{}</a>',
            f'/admin/lexy/lawyer/{obj.lawyer.id}/change/',
            obj.lawyer.name
        )

    lawyer_link.short_description = 'Юрист'

    def duration_display(self, obj):
        """Форматированная длительность"""
        return obj.formatted_duration

    duration_display.short_description = 'Длительность'

    def messages_preview(self, obj):
        """Превью последних сообщений"""
        messages = obj.messages.order_by('-timestamp')[:5]
        html = '<div style="max-height: 300px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 5px;">'

        for msg in messages:
            bg_color = '#e3f2fd' if msg.sender == 'lawyer' else '#f5f5f5'
            align = 'left' if msg.sender == 'lawyer' else 'right'
            sender_display = 'Юрист' if msg.sender == 'lawyer' else 'Клиент'

            html += format_html(
                '''
                <div style="margin: 5px 0; padding: 8px; background: {}; border-radius: 10px; text-align: {};">
                    <small><strong>{}:</strong> {}</small><br>
                    <span style="font-size: 12px;">{}</span>
                </div>
                ''',
                bg_color, align, sender_display,
                msg.message[:100] + '...' if len(msg.message) > 100 else msg.message,
                msg.timestamp.strftime('%H:%M %d.%m.%Y')
            )

        html += '</div>'
        return mark_safe(html)

    messages_preview.short_description = 'Последние сообщения'

    def mark_as_completed(self, request, queryset):
        """Пометить чаты как завершенные"""
        queryset.update(status='completed', archived_at=timezone.now())
        self.message_user(request, f"{queryset.count()} чатов завершены")

    mark_as_completed.short_description = "Завершить чаты"

    def mark_as_archived(self, request, queryset):
        """Пометить чаты как архивные"""
        queryset.update(status='archived', archived_at=timezone.now())
        self.message_user(request, f"{queryset.count()} чатов перемещены в архив")

    mark_as_archived.short_description = "Архивировать чаты"

    def export_chats(self, request, queryset):
        """Экспорт чатов (заглушка)"""
        self.message_user(request, f"Экспорт {queryset.count()} чатов начат")

    export_chats.short_description = "Экспортировать чаты"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_chat_info', 'sender_display', 'short_message',
                    'timestamp', 'is_read', 'message_type')
    list_filter = ('sender', 'message_type', 'timestamp', 'is_read')
    search_fields = ('message', 'chat__lawyer__name', 'chat__request__problem_text')
    readonly_fields = ('timestamp', 'edited_at', 'full_message_preview')

    fieldsets = (
        ('Основная информация', {
            'fields': ('chat', 'sender', 'message_type', 'is_read')
        }),
        ('Сообщение', {
            'fields': ('full_message_preview', 'message')
        }),
        ('Данные ИИ', {
            'fields': ('ai_response_data',),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('timestamp', 'edited_at', 'ip_address'),
            'classes': ('collapse',)
        }),
    )

    def get_chat_info(self, obj):
        """Информация о чате"""
        return format_html(
            'Чат #{} с {}',
            obj.chat.id,
            obj.chat.lawyer.name
        )

    get_chat_info.short_description = 'Чат'

    def sender_display(self, obj):
        """Отображаемое имя отправителя"""
        icons = {
            'client': '👤',
            'lawyer': '⚖️',
            'assistant': '🤖',
            'system': '⚙️'
        }
        return f"{icons.get(obj.sender, '❓')} {obj.get_sender_display()}"

    sender_display.short_description = 'Отправитель'

    def short_message(self, obj):
        """Краткое сообщение"""
        if len(obj.message) > 50:
            return obj.message[:50] + '...'
        return obj.message

    short_message.short_description = 'Сообщение'

    def full_message_preview(self, obj):
        """Полное превью сообщения"""
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{}</div>',
            obj.message.replace('\n', '<br>')
        )

    full_message_preview.short_description = 'Превью сообщения'


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('id', 'lawyer', 'consultation_type', 'status', 'scheduled_at',
                    'duration_minutes', 'price_display', 'is_paid', 'created_at')
    list_filter = ('consultation_type', 'status', 'is_paid', 'scheduled_at', 'created_at')
    search_fields = ('lawyer__name', 'chat__request__problem_text', 'client_feedback')

    fieldsets = (
        ('Основная информация', {
            'fields': ('chat', 'lawyer', 'consultation_type', 'status')
        }),
        ('Время и длительность', {
            'fields': ('scheduled_at', 'started_at', 'completed_at', 'duration_minutes')
        }),
        ('Финансы', {
            'fields': ('price', 'is_paid')
        }),
        ('Обратная связь', {
            'fields': ('client_rating', 'client_feedback'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def price_display(self, obj):
        """Форматированная цена"""
        return f"{obj.price} руб."

    price_display.short_description = 'Стоимость'


@admin.register(LawyerReview)
class LawyerReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'lawyer', 'client_name', 'rating_stars', 'is_verified',
                    'is_approved', 'created_at')
    list_filter = ('rating', 'is_verified', 'is_approved', 'created_at')
    search_fields = ('client_name', 'client_email', 'comment', 'lawyer__name')
    list_editable = ('is_verified', 'is_approved')

    fieldsets = (
        ('Основная информация', {
            'fields': ('lawyer', 'consultation')
        }),
        ('Данные клиента', {
            'fields': ('client_name', 'client_email')
        }),
        ('Отзыв', {
            'fields': ('rating', 'comment')
        }),
        ('Модерация', {
            'fields': ('is_verified', 'is_approved')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def rating_stars(self, obj):
        """Звезды рейтинга"""
        return obj.rating_stars

    rating_stars.short_description = 'Оценка'


# Кастомизация админ-панели
admin.site.site_header = "LEXy Администрирование"
admin.site.site_title = "LEXy Юридическое агентство"
admin.site.index_title = "Панель управления"