# lexy/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from .models import EmergencyRequest
from .forms import EmergencyRequestForm


def home(request):
    """Главная страница"""
    form = EmergencyRequestForm()
    return render(request, 'lexy/home.html', {'form': form})


@csrf_exempt  # На время разработки, потом убрать
@require_POST
def submit_request(request):
    """Обработка AJAX запроса на создание заявки"""

    # Парсим JSON данные, если они пришли
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
        # Или берем из формы
        problem_text = request.POST.get('problem_text', '')

    # Проверяем минимальную длину
    if len(problem_text.strip()) < 20:
        return JsonResponse({
            'success': False,
            'error': 'Опишите проблему подробнее (минимум 20 символов)'
        }, status=400)

    try:
        # Создаем запрос в базе данных
        request_obj = EmergencyRequest.objects.create(
            problem_text=problem_text.strip(),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            session_key=request.session.session_key or ''
        )

        # Сохраняем ID запроса в сессии
        request.session['current_request_id'] = request_obj.id

        return JsonResponse({
            'success': True,
            'request_id': request_obj.id,
            'message': 'Запрос успешно создан!',
            'redirect_url': f'/request/{request_obj.id}/'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Произошла ошибка: {str(e)}'
        }, status=500)


def request_status(request, request_id):
    """Страница статуса запроса"""
    try:
        request_obj = EmergencyRequest.objects.get(id=request_id)
        return render(request, 'lexy/request_status.html', {
            'request': request_obj
        })
    except EmergencyRequest.DoesNotExist:
        return render(request, 'lexy/404.html', status=404)


def how_it_works(request):
    """Страница "Как это работает" """
    return render(request, 'lexy/how_it_works.html')