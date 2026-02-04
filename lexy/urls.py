# lexy/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Главная и формы
    path('', views.home, name='home'),
    path('how-it-works/', views.how_it_works, name='how_it_works'),
    path('submit-request/', views.submit_request, name='submit_request'),
    path('request/<int:request_id>/', views.request_status, name='request_status'),
    path('api/check-analysis/<int:request_id>/', views.check_analysis_status, name='check_analysis_status'),

    # Юристы
    path('lawyers/', views.all_lawyers, name='all_lawyers'),
    path('find-lawyers/<int:request_id>/', views.find_lawyers, name='find_lawyers'),
    path('auto-chat/<int:request_id>/<str:specialization_code>/', views.auto_start_chat, name='auto_start_chat'),
    path('lawyer/<str:specialization_code>/', views.lawyer_detail, name='lawyer_detail'),

    # Чат
    path('start-chat/<str:specialization_code>/', views.start_chat, name='start_chat'),
    path('chat/<int:chat_id>/', views.chat_view, name='chat_view'),
    path('api/send-message/<int:chat_id>/', views.send_message, name='send_message'),
    path('api/chat-messages/<int:chat_id>/', views.get_chat_messages, name='get_chat_messages'),

    # Новые endpoints для управления контекстом
    path('api/close-chat/<int:chat_id>/', views.close_chat, name='close_chat'),
    path('api/reset-context/<int:chat_id>/', views.reset_chat_context, name='reset_chat_context'),
    path('api/debug-context/<int:chat_id>/', views.debug_chat_context, name='debug_chat_context'),
]