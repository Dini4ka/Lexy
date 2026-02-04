# lexy/models.py
from django.db import models
from django.core.validators import MinLengthValidator
import json
from django.utils import timezone


class EmergencyRequest(models.Model):
    """Модель для хранения юридических запросов"""

    STATUS_CHOICES = [
        ('pending', 'Ожидает анализа'),
        ('analyzing', 'Анализируется ИИ'),
        ('completed', 'Анализ завершен'),
        ('failed', 'Ошибка анализа'),
    ]

    URGENCY_CHOICES = [
        ('low', 'Низкая'),
        ('medium', 'Средняя'),
        ('high', 'Высокая'),
        ('critical', 'Критическая'),
    ]

    problem_text = models.TextField(
        validators=[MinLengthValidator(20)],
        verbose_name="Описание проблемы"
    )

    # Ответ от ИИ
    ai_response = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Ответ ИИ-ассистента"
    )

    response_format = models.CharField(
        max_length=10,
        choices=[('json', 'JSON'), ('text', 'Текст')],
        default='json',
        verbose_name="Формат ответа"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Статус"
    )

    # Быстрый доступ к ключевым полям
    category = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Категория дела"
    )

    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        blank=True,
        verbose_name="Срочность"
    )

    confidence = models.FloatField(
        default=0.0,
        verbose_name="Уверенность анализа"
    )

    summary = models.TextField(
        blank=True,
        verbose_name="Краткое резюме"
    )

    error_message = models.TextField(
        blank=True,
        verbose_name="Сообщение об ошибке"
    )

    # Метаданные
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP адрес"
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )

    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name="Ключ сессии"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    analyzed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата анализа"
    )

    class Meta:
        verbose_name = "Юридический запрос"
        verbose_name_plural = "Юридические запросы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Запрос #{self.id}: {self.problem_text[:50]}..."

    @property
    def is_analyzed(self):
        """Проверка завершения анализа"""
        return self.status == 'completed'

    @property
    def analysis_duration(self):
        """Длительность анализа"""
        if self.analyzed_at and self.created_at:
            return self.analyzed_at - self.created_at
        return None

    def get_formatted_response(self):
        """Получить отформатированный ответ"""
        if not self.ai_response:
            return None

        if self.response_format == 'json':
            try:
                if isinstance(self.ai_response, str):
                    data = json.loads(self.ai_response)
                else:
                    data = self.ai_response

                return {
                    'analysis': data.get('analysis', {}),
                    'recommendations': data.get('recommendations', {}),
                    'legal_references': data.get('legal_references', {}),
                    'lawyer_match': data.get('lawyer_match', {}),
                    'disclaimer': data.get('disclaimer', '')
                }
            except:
                return {"error": "Неверный формат JSON"}
        else:
            return {"text_response": self.ai_response}


class Lawyer(models.Model):
    """Модель для хранения информации об AI-юристах"""

    SPECIALIZATION_CHOICES = [
        ('auto', 'ДТП и автострахование'),
        ('labor', 'Трудовое право'),
        ('family', 'Семейное право'),
        ('housing', 'Жилищное право'),
        ('criminal', 'Уголовное право'),
        ('civil', 'Гражданское право'),
        ('bankruptcy', 'Банкротство'),
        ('tax', 'Налоговое право'),
        ('immigration', 'Миграционное право'),
        ('intellectual', 'Интеллектуальная собственность'),
        ('consumer', 'Защита прав потребителей'),
        ('military', 'Военное право'),
        ('arbitration', 'Арбитражные споры'),
    ]

    # Основная информация
    name = models.CharField(max_length=200, verbose_name="Имя юриста")
    specialization = models.CharField(
        max_length=50,
        choices=SPECIALIZATION_CHOICES,
        verbose_name="Специализация"
    )

    # Профессиональные данные
    experience = models.IntegerField(
        verbose_name="Опыт работы (лет)",
        default=0
    )
    rating = models.FloatField(
        default=5.0,
        verbose_name="Рейтинг",
        help_text="От 1 до 5"
    )
    cases_completed = models.IntegerField(
        default=0,
        verbose_name="Завершенных дел"
    )
    success_rate = models.FloatField(
        default=0.0,
        verbose_name="Процент успешных дел",
        help_text="В процентах (0-100)"
    )

    # Контактная информация (для демо)
    price = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Стоимость услуг"
    )
    response_time = models.CharField(
        max_length=50,
        default="1-2 часа",
        verbose_name="Время ответа"
    )
    availability = models.CharField(
        max_length=100,
        default="Пн-Пт, 9:00-18:00",
        verbose_name="График работы"
    )

    # Описание
    bio = models.TextField(
        blank=True,
        verbose_name="Биография"
    )
    education = models.TextField(
        blank=True,
        verbose_name="Образование"
    )
    certifications = models.TextField(
        blank=True,
        verbose_name="Сертификаты и лицензии"
    )

    # Внешний вид
    photo = models.ImageField(
        upload_to='lawyers/photos/',
        blank=True,
        null=True,
        verbose_name="Фотография"
    )

    # Связь с Yandex AI агентами
    assistant_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID ассистента в Yandex Cloud"
    )
    model_uri = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Model URI"
    )
    system_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Имя в системе (из инструкций)"
    )

    # Статус
    is_available = models.BooleanField(
        default=True,
        verbose_name="Доступен для консультаций"
    )
    is_verified = models.BooleanField(
        default=True,
        verbose_name="Проверенный юрист"
    )
    is_premium = models.BooleanField(
        default=False,
        verbose_name="Премиум юрист"
    )

    # Дополнительная информация для демо
    personality = models.TextField(
        blank=True,
        help_text="Описание характера и стиля общения"
    )
    demo_messages = models.JSONField(
        default=list,
        blank=True,
        help_text="Примерные сообщения для демо"
    )

    # Метки для поиска
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Метки для поиска"
    )

    # Статистика
    average_response_time_minutes = models.IntegerField(
        default=60,
        verbose_name="Среднее время ответа (минут)"
    )
    client_satisfaction = models.FloatField(
        default=0.0,
        verbose_name="Удовлетворенность клиентов"
    )

    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Юрист"
        verbose_name_plural = "Юристы"
        ordering = ['-rating', '-experience']

    def __str__(self):
        return f"{self.name} - {self.get_specialization_display()}"

    @property
    def specialization_display(self):
        """Отображаемое название специализации"""
        return self.get_specialization_display()

    @property
    def formatted_rating(self):
        """Форматированный рейтинг"""
        return f"{self.rating:.1f}"

    @property
    def years_experience(self):
        """Опыт работы в годах"""
        return f"{self.experience} лет"

    @property
    def is_ai_lawyer(self):
        """Проверка, является ли юрист AI-агентом"""
        return bool(self.assistant_id)

    def get_matching_specialization(self, category):
        """Получить специализацию, соответствующую категории дела"""
        category_map = {
            'dtr': 'auto',
            'dtp': 'auto',
            'work': 'labor',
            'labor': 'labor',
            'family': 'family',
            'housing': 'housing',
            'criminal': 'criminal',
            'civil': 'civil',
            'bankruptcy': 'bankruptcy',
            'tax': 'tax',
            'immigration': 'immigration',
            'intellectual': 'intellectual',
            'consumer': 'consumer',
            'military': 'military',
            'arbitration': 'arbitration',
            'other': 'civil'
        }
        return category_map.get(category, 'civil')


# models.py - исправленный класс LawyerChat
class LawyerChat(models.Model):
    """Модель для чатов с юристами"""

    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('completed', 'Завершен'),
        ('archived', 'В архиве'),
        ('pending', 'Ожидает ответа'),
        ('closed', 'Закрыт'),
    ]

    # Связи
    request = models.ForeignKey(
        'EmergencyRequest',
        on_delete=models.CASCADE,
        related_name='chats',
        verbose_name="Исходный запрос"
    )

    # Это поле ОБЯЗАТЕЛЬНОЕ и не может быть пустым
    lawyer = models.ForeignKey(
        Lawyer,
        on_delete=models.CASCADE,
        related_name='chats',
        verbose_name="Юрист"
    )

    # Новые поля для AI-агентов (сделаем их необязательными)
    lawyer_agent_id = models.CharField(
        max_length=100,
        blank=True,  # Разрешаем пустые значения
        verbose_name="ID AI-агента юриста"
    )

    lawyer_name = models.CharField(
        max_length=200,
        blank=True,  # Разрешаем пустые значения
        verbose_name="Имя юриста (из агента)"
    )

    lawyer_specialization = models.CharField(
        max_length=100,
        blank=True,  # Разрешаем пустые значения
        verbose_name="Специализация (из агента)"
    )

    # Статус чата
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Статус чата"
    )

    # Метаданные
    title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Название чата",
        help_text="Автоматически генерируется из запроса"
    )

    # Статистика
    message_count = models.IntegerField(
        default=0,
        verbose_name="Количество сообщений"
    )
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Время последнего сообщения"
    )

    # Настройки
    is_anonymous = models.BooleanField(
        default=True,
        verbose_name="Анонимный чат"
    )
    client_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Имя клиента"
    )
    client_email = models.EmailField(
        blank=True,
        verbose_name="Email клиента"
    )

    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Чат с юристом"
        verbose_name_plural = "Чаты с юристами"
        ordering = ['-last_message_at', '-created_at']

    def __str__(self):
        return f"Чат #{self.id}: {self.lawyer.name} - {self.request.problem_text[:50]}..."

    def save(self, *args, **kwargs):
        # Автоматически генерируем название чата при создании
        if not self.title:
            lawyer_name = self.lawyer.name if self.lawyer else (self.lawyer_name or 'юристом')
            self.title = f"Консультация с {lawyer_name} по вопросу: {self.request.problem_text[:50]}..."

        # Сохраняем объект сначала
        super().save(*args, **kwargs)

        # Только после сохранения (когда есть primary key) можно проверять сообщения
        if self.messages.exists():
            last_msg = self.messages.last()
            self.last_message_at = last_msg.timestamp
            # Сохраняем еще раз с обновленным временем
            super().save(update_fields=['last_message_at'])


class ChatMessage(models.Model):
    """Модель для сообщений в чате"""

    SENDER_CHOICES = [
        ('client', 'Клиент'),
        ('lawyer', 'Юрист'),
        ('system', 'Система'),
        ('assistant', 'AI-ассистент'),
    ]

    MESSAGE_TYPES = [
        ('text', 'Текст'),
        ('document', 'Документ'),
        ('image', 'Изображение'),
        ('audio', 'Аудио'),
        ('video', 'Видео'),
    ]

    # Связи
    chat = models.ForeignKey(
        LawyerChat,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Чат"
    )

    # Основные поля
    sender = models.CharField(
        max_length=20,
        choices=SENDER_CHOICES,
        verbose_name="Отправитель"
    )
    message = models.TextField(
        verbose_name="Сообщение"
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPES,
        default='text',
        verbose_name="Тип сообщения"
    )

    # Статус
    is_read = models.BooleanField(
        default=False,
        verbose_name="Прочитано"
    )
    is_edited = models.BooleanField(
        default=False,
        verbose_name="Редактировано"
    )

    # Для ответов от ИИ-юриста
    ai_response_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Данные ответа ИИ"
    )

    # Метаданные
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP адрес отправителя"
    )

    # Системные поля
    timestamp = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Сообщение чата"
        verbose_name_plural = "Сообщения чатов"
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.get_sender_display()}: {self.message[:50]}..."

    def save(self, *args, **kwargs):
        # При сохранении нового сообщения обновляем счетчик в чате
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            self.chat.message_count += 1
            self.chat.last_message_at = self.timestamp
            self.chat.save(update_fields=['message_count', 'last_message_at'])

    @property
    def formatted_time(self):
        """Форматированное время"""
        return self.timestamp.strftime("%H:%M")

    @property
    def formatted_date(self):
        """Форматированная дата"""
        return self.timestamp.strftime("%d.%m.%Y")

    @property
    def is_from_client(self):
        """Сообщение от клиента"""
        return self.sender == 'client'

    @property
    def is_from_lawyer(self):
        """Сообщение от юриста"""
        return self.sender in ['lawyer', 'assistant']

    def mark_as_read(self):
        """Пометить сообщение как прочитанное"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])


class Consultation(models.Model):
    """Модель для консультаций (расширенная информация)"""

    TYPE_CHOICES = [
        ('chat', 'Чат-консультация'),
        ('call', 'Телефонная консультация'),
        ('video', 'Видео-консультация'),
        ('meeting', 'Личная встреча'),
        ('document', 'Подготовка документов'),
    ]

    STATUS_CHOICES = [
        ('requested', 'Запрошена'),
        ('confirmed', 'Подтверждена'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
        ('rescheduled', 'Перенесена'),
    ]

    # Связи
    chat = models.OneToOneField(
        LawyerChat,
        on_delete=models.CASCADE,
        related_name='consultation',
        verbose_name="Чат"
    )
    lawyer = models.ForeignKey(
        Lawyer,
        on_delete=models.CASCADE,
        related_name='consultations',
        verbose_name="Юрист"
    )

    # Основные данные
    consultation_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='chat',
        verbose_name="Тип консультации"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='requested',
        verbose_name="Статус"
    )

    # Время и дата
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Запланировано на"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Начало консультации"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Окончание консультации"
    )

    # Детали
    duration_minutes = models.IntegerField(
        default=0,
        verbose_name="Длительность (минут)"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Стоимость"
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name="Оплачено"
    )

    # Обратная связь
    client_rating = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Оценка клиента"
    )
    client_feedback = models.TextField(
        blank=True,
        verbose_name="Отзыв клиента"
    )

    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Консультация"
        verbose_name_plural = "Консультации"
        ordering = ['-scheduled_at', '-created_at']

    def __str__(self):
        return f"Консультация #{self.id} с {self.lawyer.name}"

    @property
    def is_completed(self):
        """Завершена ли консультация"""
        return self.status == 'completed'

    @property
    def actual_duration(self):
        """Фактическая длительность"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() / 60
        return self.duration_minutes

    @property
    def formatted_price(self):
        """Форматированная цена"""
        return f"{self.price} руб."


class LawyerReview(models.Model):
    """Модель для отзывов о юристах"""

    RATING_CHOICES = [
        (1, '★☆☆☆☆'),
        (2, '★★☆☆☆'),
        (3, '★★★☆☆'),
        (4, '★★★★☆'),
        (5, '★★★★★'),
    ]

    lawyer = models.ForeignKey(
        Lawyer,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Юрист"
    )

    # Данные клиента
    client_name = models.CharField(
        max_length=100,
        verbose_name="Имя клиента"
    )
    client_email = models.EmailField(
        blank=True,
        verbose_name="Email клиента"
    )

    # Отзыв
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        verbose_name="Оценка"
    )
    comment = models.TextField(
        verbose_name="Комментарий"
    )

    # Метаданные
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name="Консультация"
    )

    # Модерация
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Проверенный отзыв"
    )
    is_approved = models.BooleanField(
        default=True,
        verbose_name="Одобрен к публикации"
    )

    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Отзыв о юристе"
        verbose_name_plural = "Отзывы о юристах"
        ordering = ['-created_at']

    def __str__(self):
        return f"Отзыв на {self.lawyer.name} от {self.client_name}"

    @property
    def rating_stars(self):
        """Звезды рейтинга"""
        return '★' * self.rating + '☆' * (5 - self.rating)


# Сигналы для автоматического обновления статистики
from django.db.models import Avg, Count
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=LawyerReview)
def update_lawyer_stats(sender, instance, created, **kwargs):
    """Обновление статистики юриста при добавлении отзыва"""
    if created and instance.is_approved:
        lawyer = instance.lawyer

        # Обновляем рейтинг
        reviews = lawyer.reviews.filter(is_approved=True)
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        if avg_rating:
            lawyer.rating = round(avg_rating, 1)

        # Обновляем количество отзывов
        lawyer.cases_completed = reviews.count()

        # Обновляем процент успешных дел (для демо - случайное значение)
        import random
        if lawyer.success_rate == 0:
            lawyer.success_rate = round(random.uniform(70, 98), 1)

        lawyer.save(update_fields=['rating', 'cases_completed', 'success_rate'])


@receiver(post_save, sender=ChatMessage)
def update_chat_stats(sender, instance, created, **kwargs):
    """Обновление статистики чата при добавлении сообщения"""
    if created:
        # Обновляем время последнего сообщения в чате
        instance.chat.last_message_at = instance.timestamp
        instance.chat.save(update_fields=['last_message_at'])