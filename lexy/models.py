# lexy/models.py
from django.db import models
from django.utils import timezone


class EmergencyRequest(models.Model):
    """Модель для хранения экстренных запросов помощи"""

    CATEGORY_CHOICES = [
        ('dtr', 'ДТП'),
        ('criminal', 'Уголовное дело'),
        ('work', 'Трудовое право'),
        ('family', 'Семейное право'),
        ('housing', 'Жилищное право'),
        ('civil', 'Гражданское право'),
        ('other', 'Другое'),
    ]

    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('ai_analyzed', 'Проанализирован ИИ'),
        ('lawyer_assigned', 'Назначен юрист'),
        ('closed', 'Закрыт'),
    ]

    # Основные данные
    problem_text = models.TextField('Описание проблемы')
    category = models.CharField('Категория', max_length=20, choices=CATEGORY_CHOICES, default='other')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')

    # Контактные данные (опциональные на первом этапе)
    user_phone = models.CharField('Телефон', max_length=20, blank=True, null=True)
    user_email = models.EmailField('Email', blank=True, null=True)

    # Технические данные
    ip_address = models.GenericIPAddressField('IP адрес', blank=True, null=True)
    user_agent = models.TextField('User Agent', blank=True)
    session_key = models.CharField('Ключ сессии', max_length=40, blank=True)

    # Временные метки
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    ai_processed_at = models.DateTimeField('Обработано ИИ', null=True, blank=True)

    class Meta:
        verbose_name = 'Запрос помощи'
        verbose_name_plural = 'Запросы помощи'
        ordering = ['-created_at']

    def __str__(self):
        return f"Запрос #{self.id} - {self.get_category_display()} - {self.created_at.strftime('%d.%m.%Y %H:%M')}"