# lexy/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from django.utils import timezone
import threading
from django.core.cache import cache

from .models import EmergencyRequest, LawyerChat, ChatMessage, Lawyer
from .forms import EmergencyRequestForm
from .yandex_utils import (
    get_lawyer_agent_by_specialization,
    get_all_lawyer_agents,
    analyze_with_assistant,
    chat_with_lawyer,
    AGENTS
)


def home(request):
    """Главная страница"""
    form = EmergencyRequestForm()
    return render(request, 'lexy/home.html', {'form': form})


@csrf_exempt
@require_POST
def submit_request(request):
    """Обработка AJAX запроса на создание заявки"""
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            problem_text = data.get('problem_text', '')
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Некорректный формат данных'
            }, status=400)
    else:
        problem_text = request.POST.get('problem_text', '')

    if len(problem_text.strip()) < 20:
        return JsonResponse({
            'success': False,
            'error': 'Опишите проблему подробнее (минимум 20 символов)'
        }, status=400)

    try:
        # Создаем запрос
        request_obj = EmergencyRequest.objects.create(
            problem_text=problem_text.strip(),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            session_key=request.session.session_key or '',
            status='analyzing'
        )

        # Сохраняем ID запроса в сессии
        request.session['current_request_id'] = request_obj.id

        # Запускаем анализ в отдельном потоке
        thread = threading.Thread(
            target=analyze_with_yandex_assistant,
            args=(request_obj.id, problem_text.strip())
        )
        thread.daemon = True
        thread.start()

        return JsonResponse({
            'success': True,
            'request_id': request_obj.id,
            'redirect_url': f'/request/{request_obj.id}/'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Произошла ошибка: {str(e)}'
        }, status=500)


def analyze_with_yandex_assistant(request_id, problem_text):
    """Анализ ситуации через Yandex Assistant API"""
    from .models import EmergencyRequest

    try:
        request_obj = EmergencyRequest.objects.get(id=request_id)
        assistant_id = AGENTS['general']['id']

        ai_response = analyze_with_assistant(assistant_id, problem_text)

        if 'error' not in ai_response:
            request_obj.ai_response = ai_response
            request_obj.status = 'completed'
            request_obj.analyzed_at = timezone.now()

            if isinstance(ai_response, dict):
                request_obj.response_format = 'json'
                analysis = ai_response.get('analysis', {})
                request_obj.category = analysis.get('category', 'other')
                request_obj.urgency = analysis.get('urgency', 'medium')
                request_obj.confidence = analysis.get('confidence', 0.0)
                request_obj.summary = analysis.get('summary', '')
            else:
                request_obj.response_format = 'text'
                request_obj.summary = str(ai_response)[:200] + '...' if len(str(ai_response)) > 200 else str(
                    ai_response)
        else:
            request_obj.ai_response = {"error": "Ассистент не ответил"}
            request_obj.response_format = 'json'
            request_obj.status = 'completed'
            request_obj.summary = "Ассистент не смог проанализировать ситуацию"

        request_obj.save()

    except Exception as e:
        try:
            request_obj = EmergencyRequest.objects.get(id=request_id)
            request_obj.status = 'failed'
            request_obj.error_message = str(e)
            request_obj.save()
        except:
            pass


def request_status(request, request_id):
    """Страница статуса запроса с результатом анализа"""
    try:
        request_obj = EmergencyRequest.objects.get(id=request_id)

        context = {
            'request': request_obj,
            'show_refresh': request_obj.status == 'analyzing'
        }

        if request_obj.status == 'completed' and request_obj.ai_response:
            if request_obj.response_format == 'json':
                context['response'] = format_json_response(request_obj.ai_response)
            else:
                context['response'] = format_text_response(request_obj.ai_response)

        return render(request, 'lexy/request_status.html', context)

    except EmergencyRequest.DoesNotExist:
        return render(request, 'lexy/404.html', status=404)


def format_json_response(data):
    """Форматирование JSON ответа для HTML шаблона"""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            return {"error": "Неверный формат ответа"}

    formatted = {
        'analysis': data.get('analysis', {}),
        'recommendations': data.get('recommendations', {}),
        'legal_references': data.get('legal_references', {}),
        'lawyer_match': data.get('lawyer_match', {}),
        'disclaimer': data.get('disclaimer', '')
    }

    if not formatted['analysis']:
        formatted['analysis'] = {
            'category': 'general',
            'confidence': 0.7,
            'summary': 'Анализ выполнен',
            'urgency': 'medium'
        }

    return formatted


def format_text_response(text):
    """Форматирование текстового ответа"""
    return {
        'text_response': text,
        'analysis': {
            'summary': text[:200] + '...' if len(text) > 200 else text,
            'category': 'general',
            'urgency': 'medium',
            'confidence': 0.7
        }
    }


def check_analysis_status(request, request_id):
    """API endpoint для проверки статуса анализа"""
    try:
        request_obj = EmergencyRequest.objects.get(id=request_id)

        response_data = {
            'status': request_obj.status,
            'has_response': bool(request_obj.ai_response),
            'category': request_obj.category,
            'urgency': request_obj.urgency
        }

        if request_obj.status == 'completed' and request_obj.ai_response:
            response_data['response'] = request_obj.ai_response
            response_data['summary'] = request_obj.summary

        return JsonResponse(response_data)

    except EmergencyRequest.DoesNotExist:
        return JsonResponse({'error': 'Запрос не найден'}, status=404)


def how_it_works(request):
    """Страница "Как это работает" """
    return render(request, 'lexy/how_it_works.html')


def find_lawyers(request, request_id):
    """Страница подбора AI-юристов"""
    emergency_request = get_object_or_404(EmergencyRequest, id=request_id)

    # Проверяем, есть ли уже чат
    existing_chat = LawyerChat.objects.filter(request=emergency_request).first()

    # Определяем специализацию с помощью Yandex AI
    from .yandex_utils import determine_lawyer_specialization
    recommended_code = determine_lawyer_specialization(emergency_request.problem_text)

    if not recommended_code:
        recommended_code = emergency_request.category or 'civil'

    # Получаем всех доступных AI-юристов
    all_lawyers = get_all_lawyer_agents()

    # Создаем список юристов, рекомендованного ставим первым
    lawyers = []
    recommended_lawyer_added = False

    for spec_code, lawyer_data in all_lawyers.items():
        is_recommended = spec_code == recommended_code
        lawyer_info = {
            'id': spec_code,
            'name': lawyer_data['name'],
            'specialization': lawyer_data['specialization'],
            'personality': lawyer_data['personality'],
            'response_time': lawyer_data['response_time'],
            'agent_id': lawyer_data['id'],
            'is_recommended': is_recommended
        }

        # Рекомендованного ставим первым
        if is_recommended:
            lawyers.insert(0, lawyer_info)
            recommended_lawyer_added = True
        else:
            lawyers.append(lawyer_info)

    # Если рекомендованный юрист не найден, берем первого
    if not recommended_lawyer_added and lawyers:
        lawyers[0]['is_recommended'] = True

    context = {
        'request': emergency_request,
        'lawyers': lawyers,
        'existing_chat': existing_chat,
    }

    return render(request, 'lexy/find_lawyers.html', context)


def auto_start_chat(request, request_id, specialization_code):
    """Автоматически начать чат с подходящим AI-юристом"""
    emergency_request = get_object_or_404(EmergencyRequest, id=request_id)

    # Получаем данные юриста
    lawyer_data = get_lawyer_agent_by_specialization(specialization_code)

    if not lawyer_data:
        return redirect('find_lawyers', request_id=request_id)

    try:
        # Сначала создаем или получаем объект Lawyer в базе
        lawyer_obj, created = Lawyer.objects.get_or_create(
            name=lawyer_data['name'],
            defaults={
                'specialization': specialization_code,
                'experience': 8 if specialization_code == 'labor' else 12 if specialization_code == 'auto' else 10,
                'rating': 4.8,
                'cases_completed': 150,
                'success_rate': 85.5,
                'bio': lawyer_data.get('personality', ''),
                'is_available': True,
                'is_verified': True,
                'response_time': lawyer_data.get('response_time', '1-2 часа'),
                'price': 'Консультация бесплатно',
                'availability': 'Пн-Пт, 9:00-18:00',
                'assistant_id': lawyer_data['id']
            }
        )

        # Проверяем, нет ли уже чата с этим юристом
        existing_chat = LawyerChat.objects.filter(
            request=emergency_request,
            lawyer=lawyer_obj
        ).first()

        if existing_chat:
            return redirect('chat_view', chat_id=existing_chat.id)

        # Создаем чат с ОБЯЗАТЕЛЬНЫМ полем lawyer
        chat = LawyerChat.objects.create(
            request=emergency_request,
            lawyer=lawyer_obj,
            lawyer_agent_id=lawyer_data['id'],
            lawyer_name=lawyer_data['name'],
            lawyer_specialization=lawyer_data['specialization'],
            status='active',
            title=f"Консультация с {lawyer_data['name']}"
        )

        # Создаем системное сообщение
        ChatMessage.objects.create(
            chat=chat,
            sender='system',
            message=f"Чат начат с {lawyer_data['name']}. Специализация: {lawyer_data['specialization']}."
        )

        # Добавляем описание проблемы как первое сообщение от клиента
        ChatMessage.objects.create(
            chat=chat,
            sender='client',
            message=emergency_request.problem_text[:500]
        )

        # Получаем приветствие от AI-юриста с передачей chat.id для создания conversation
        messages_history = [{
            'role': 'user',
            'content': emergency_request.problem_text[:500]
        }]

        # Передаем chat.id для создания conversation в Yandex AI
        ai_response = chat_with_lawyer(lawyer_data['id'], messages_history, chat.id)

        # Формируем ответ юриста
        if isinstance(ai_response, dict):
            if 'message' in ai_response:
                lawyer_message = ai_response['message']
            elif 'lawyer_name' in ai_response and 'message' in ai_response:
                lawyer_message = ai_response['message']
            else:
                lawyer_message = f"Здравствуйте! Я {lawyer_data['name']}, {lawyer_data['specialization'].lower()}. Как я могу вам помочь?"
        else:
            lawyer_message = str(ai_response)

        # Сохраняем сообщение юриста
        ChatMessage.objects.create(
            chat=chat,
            sender='lawyer',
            message=lawyer_message[:2000],
            ai_response_data=ai_response if isinstance(ai_response, dict) else None
        )

        # Обновляем время последнего сообщения
        chat.last_message_at = timezone.now()
        chat.save()

        return redirect('chat_view', chat_id=chat.id)

    except Exception as e:
        print(f"Ошибка создания чата: {e}")
        import traceback
        traceback.print_exc()
        return redirect('find_lawyers', request_id=request_id)


@csrf_exempt
@require_POST
def start_chat(request, specialization_code):
    """Начать чат с AI-юристом по специализации"""
    # Получаем данные юриста
    lawyer_data = get_lawyer_agent_by_specialization(specialization_code)

    if not lawyer_data:
        return JsonResponse({'success': False, 'error': 'Юрист не найден'})

    # Получаем ID запроса
    request_id = request.POST.get('request_id') or request.session.get('current_request_id')

    if not request_id:
        return JsonResponse({'success': False, 'error': 'Не найден запрос'})

    emergency_request = get_object_or_404(EmergencyRequest, id=request_id)

    try:
        # Создаем или получаем юриста
        lawyer_obj, created = Lawyer.objects.get_or_create(
            name=lawyer_data['name'],
            defaults={
                'specialization': specialization_code,
                'experience': 8 if specialization_code == 'labor' else 12 if specialization_code == 'auto' else 10,
                'rating': 4.8,
                'cases_completed': 150,
                'success_rate': 85.5,
                'bio': lawyer_data.get('personality', ''),
                'is_available': True,
                'is_verified': True,
                'response_time': lawyer_data.get('response_time', '1-2 часа'),
                'price': 'Консультация бесплатно',
                'availability': 'Пн-Пт, 9:00-18:00',
                'assistant_id': lawyer_data['id']
            }
        )

        # Создаем чат
        chat = LawyerChat.objects.create(
            request=emergency_request,
            lawyer=lawyer_obj,
            lawyer_agent_id=lawyer_data['id'],
            lawyer_name=lawyer_data['name'],
            lawyer_specialization=lawyer_data['specialization'],
            status='active',
            title=f"Консультация с {lawyer_data['name']}"
        )

        # Создаем системное сообщение
        ChatMessage.objects.create(
            chat=chat,
            sender='system',
            message=f"Чат начат с {lawyer_data['name']}. Специализация: {lawyer_data['specialization']}."
        )

        # Добавляем описание проблемы как первое сообщение
        ChatMessage.objects.create(
            chat=chat,
            sender='client',
            message=emergency_request.problem_text[:500]
        )

        # Получаем приветствие от AI-юриста
        messages_history = [{
            'role': 'user',
            'content': emergency_request.problem_text[:500]
        }]

        ai_response = chat_with_lawyer(lawyer_data['id'], messages_history, chat.id)

        # Формируем ответ юриста
        if isinstance(ai_response, dict):
            if 'message' in ai_response:
                lawyer_message = ai_response['message']
            elif 'lawyer_name' in ai_response and 'message' in ai_response:
                lawyer_message = ai_response['message']
            else:
                lawyer_message = f"Здравствуйте! Я {lawyer_data['name']}, {lawyer_data['specialization'].lower()}. Как я могу вам помочь?"
        else:
            lawyer_message = str(ai_response)

        ChatMessage.objects.create(
            chat=chat,
            sender='lawyer',
            message=lawyer_message[:2000],
            ai_response_data=ai_response if isinstance(ai_response, dict) else None
        )

        return JsonResponse({
            'success': True,
            'chat_id': chat.id,
            'redirect_url': f'/chat/{chat.id}/'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def chat_view(request, chat_id):
    """Страница чата с AI-юристом"""
    chat = get_object_or_404(LawyerChat, id=chat_id)
    messages = chat.messages.all().order_by('timestamp')

    # Получаем объект юриста из базы
    lawyer_obj = chat.lawyer if hasattr(chat, 'lawyer') and chat.lawyer else None

    # Создаем объект "юриста" для шаблона
    lawyer = {
        'name': chat.lawyer_name if chat.lawyer_name else (lawyer_obj.name if lawyer_obj else 'Юрист'),
        'specialization': chat.lawyer_specialization if chat.lawyer_specialization else (
            lawyer_obj.get_specialization_display() if lawyer_obj else ''),
        'agent_id': chat.lawyer_agent_id
    }

    # Добавляем photo если есть
    if lawyer_obj and lawyer_obj.photo:
        lawyer['photo'] = lawyer_obj.photo

    context = {
        'chat': chat,
        'messages': messages,
        'lawyer': lawyer,
        'request': chat.request,
    }

    return render(request, 'lexy/chat.html', context)


@csrf_exempt
@require_POST
def send_message(request, chat_id):
    """Отправить сообщение в чат с использованием Conversations API"""
    chat = get_object_or_404(LawyerChat, id=chat_id)

    data = json.loads(request.body)
    message_text = data.get('message', '').strip()

    if not message_text:
        return JsonResponse({'success': False, 'error': 'Сообщение не может быть пустым'})

    try:
        # Сохраняем сообщение клиента
        ChatMessage.objects.create(
            chat=chat,
            sender='client',
            message=message_text
        )

        # Подготавливаем историю сообщений для логики приложения
        recent_messages = list(chat.messages.order_by('-timestamp')[:10])
        recent_messages.reverse()

        messages_history = []
        for msg in recent_messages:
            if msg.sender == 'client':
                messages_history.append({
                    'role': 'user',
                    'content': msg.message
                })
            elif msg.sender == 'lawyer':
                messages_history.append({
                    'role': 'assistant',
                    'content': msg.message
                })

        # Ключевое изменение: передаем chat.id для использования Conversations API
        ai_response = chat_with_lawyer(chat.lawyer_agent_id, messages_history, chat.id)

        # Сохраняем ответ
        if isinstance(ai_response, dict):
            if 'message' in ai_response:
                lawyer_message = ai_response['message']
            else:
                # Если ответ содержит другие поля, формируем читаемое сообщение
                if 'lawyer_name' in ai_response and 'questions_to_client' in ai_response:
                    # Формируем структурированный ответ
                    response_parts = [f"{ai_response.get('message', '')}"]

                    if ai_response.get('questions_to_client'):
                        response_parts.append("\n\nВопросы для уточнения:")
                        for i, question in enumerate(ai_response['questions_to_client'], 1):
                            response_parts.append(f"{i}. {question}")

                    if ai_response.get('action_plan'):
                        response_parts.append("\nПлан действий:")
                        for i, step in enumerate(ai_response['action_plan'], 1):
                            response_parts.append(f"{i}. {step}")

                    lawyer_message = "\n".join(response_parts)
                else:
                    lawyer_message = json.dumps(ai_response, ensure_ascii=False, indent=2)
        else:
            lawyer_message = str(ai_response)

        ChatMessage.objects.create(
            chat=chat,
            sender='lawyer',
            message=lawyer_message[:2000],
            ai_response_data=ai_response if isinstance(ai_response, dict) else None
        )

        # Обновляем время последнего сообщения в чате
        chat.last_message_at = timezone.now()
        chat.save()

        return JsonResponse({
            'success': True,
            'message': lawyer_message,
            'sender': 'lawyer'
        })

    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


def all_lawyers(request):
    """Страница со всеми AI-юристами"""
    # Получаем всех доступных AI-юристов
    all_lawyers_data = get_all_lawyer_agents()

    # Преобразуем в список для шаблона
    lawyers_list = []
    for spec_code, lawyer_data in all_lawyers_data.items():
        lawyers_list.append({
            'id': spec_code,
            'name': lawyer_data['name'],
            'specialization': lawyer_data['specialization'],
            'personality': lawyer_data.get('personality', ''),
            'response_time': lawyer_data.get('response_time', '1-2 часа')
        })

    context = {
        'lawyers': lawyers_list,
    }

    return render(request, 'lexy/all_lawyers.html', context)


def lawyer_detail(request, specialization_code):
    """Страница деталей AI-юриста"""
    # Получаем юриста по специализации
    lawyer_data = get_lawyer_agent_by_specialization(specialization_code)

    if not lawyer_data:
        return render(request, 'lexy/404.html', status=404)

    context = {
        'lawyer': {
            'id': specialization_code,
            'name': lawyer_data['name'],
            'specialization': lawyer_data['specialization'],
            'personality': lawyer_data.get('personality', ''),
            'response_time': lawyer_data.get('response_time', '1-2 часа'),
            'description': lawyer_data.get('description', '')
        }
    }

    return render(request, 'lexy/lawyer_detail.html', context)


def get_chat_messages(request, chat_id):
    """Получить сообщения чата"""
    chat = get_object_or_404(LawyerChat, id=chat_id)
    messages = chat.messages.all().order_by('timestamp')

    messages_list = []
    for msg in messages:
        messages_list.append({
            'sender': msg.sender,
            'message': msg.message,
            'timestamp': msg.timestamp.isoformat(),
        })

    return JsonResponse({
        'success': True,
        'messages': messages_list,
        'chat_status': chat.status
    })


@csrf_exempt
@require_POST
def close_chat(request, chat_id):
    """Закрыть чат и очистить conversation"""
    chat = get_object_or_404(LawyerChat, id=chat_id)

    try:
        # Закрываем чат
        chat.status = 'closed'
        chat.archived_at = timezone.now()
        chat.save()

        # Очищаем conversation из кэша
        cache_key = f"yandex_conversation_{chat_id}"
        cache.delete(cache_key)

        return JsonResponse({'success': True, 'message': 'Чат закрыт'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def reset_chat_context(request, chat_id):
    """Сбросить контекст диалога (создать новый conversation)"""
    chat = get_object_or_404(LawyerChat, id=chat_id)

    try:
        # Удаляем существующий conversation из кэша
        cache_key = f"yandex_conversation_{chat_id}"
        cache.delete(cache_key)

        # Создаем системное сообщение о сбросе контекста
        ChatMessage.objects.create(
            chat=chat,
            sender='system',
            message='Контекст диалога сброшен. Начинаем новый разговор.'
        )

        return JsonResponse({
            'success': True,
            'message': 'Контекст диалога сброшен. Следующее сообщение начнет новый разговор.'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def debug_chat_context(request, chat_id):
    """Отладка: информация о текущем conversation"""
    chat = get_object_or_404(LawyerChat, id=chat_id)

    cache_key = f"yandex_conversation_{chat_id}"
    conversation_id = cache.get(cache_key)

    messages_count = chat.messages.count()
    last_messages = list(chat.messages.order_by('-timestamp')[:3])

    debug_info = {
        'chat_id': chat_id,
        'conversation_id': conversation_id,
        'conversation_cached': bool(conversation_id),
        'total_messages': messages_count,
        'last_messages': [
            {
                'id': msg.id,
                'sender': msg.sender,
                'timestamp': msg.timestamp.isoformat(),
                'message_preview': msg.message[:50] + '...' if len(msg.message) > 50 else msg.message
            }
            for msg in last_messages
        ],
        'lawyer_agent_id': chat.lawyer_agent_id,
        'status': chat.status
    }

    return JsonResponse({'success': True, 'debug_info': debug_info})