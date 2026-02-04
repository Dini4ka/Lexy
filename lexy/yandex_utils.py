# lexy/yandex_utils.py
import json
import openai
import re
from django.conf import settings
from django.core.cache import cache
import time

# Конфигурация Yandex Cloud
YANDEX_CLOUD_API_KEY = 'AQVNz0007Rz_GVsUFteCbJQ34he2dhsdGDC7_sFr'
PROJECT_ID = 'b1ggvnsm70rqgii9kmc6'

# Инициализация клиента OpenAI с Yandex endpoint
yandex_client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=PROJECT_ID
)


# Ключ для хранения conversation_id в кэше (можно хранить в базе)
def get_conversation_cache_key(chat_id):
    return f"yandex_conversation_{chat_id}"


# Получаем или создаем conversation_id для чата
def get_or_create_conversation(chat_id):
    """Получает существующий conversation_id или создает новый"""
    cache_key = get_conversation_cache_key(chat_id)
    conversation_id = cache.get(cache_key)

    if not conversation_id:
        # Создаем новый conversation
        try:
            conversation = yandex_client.conversations.create()
            conversation_id = conversation.id
            cache.set(cache_key, conversation_id, timeout=86400)  # 24 часа
            print(f"Создан новый conversation для чата {chat_id}: {conversation_id}")
        except Exception as e:
            print(f"Ошибка создания conversation: {e}")
            return None

    return conversation_id


# Остальной код AGENTS оставляем без изменений
AGENTS = {
    'general': {
        'id': 'fvtvd2uu4hpgl9rmptqh',  # AlexyAgent
        'name': 'LEXy Ассистент',
        'type': 'analyzer'
    },
    'lawyers': {
        'family': {  # Мария Петрова
            'id': 'fvtsur6lqll4n4q4lj5g',
            'name': 'Мария Петрова',
            'specialization': 'Семейное право',
            'personality': 'Эксперт по семейным спорам',
            'response_time': '1-2 часа'
        },
        'labor': {  # Анна Ковалева
            'id': 'fvt0q9er8h746fennfel',
            'name': 'Анна Ковалева',
            'specialization': 'Трудовое право',
            'personality': 'Эмпатичный юрист с 8-летним опытом',
            'response_time': '30-60 минут'
        },
        'auto': {  # Дмитрий Соколов
            'id': 'fvtmmr90b7m270h1ik5n',
            'name': 'Дмитрий Соколов',
            'specialization': 'ДТП и автострахование',
            'personality': 'Бывший сотрудник ГИБДД',
            'response_time': '15-30 минут'
        }
    }
}


def determine_lawyer_specialization(problem_text):
    """
    Определяет подходящую специализацию юриста на основе текста проблемы
    Использует Yandex AI для анализа, а не хардкод ключевых слов
    """
    try:
        # Создаем промпт для анализа
        prompt = f"""
        Проанализируй юридическую проблему и определи, к какой специализации она относится:

        Проблема: {problem_text}

        Доступные специализации:
        1. 'auto' - ДТП, автострахование, транспортные происшествия
        2. 'labor' - трудовые споры, увольнение, зарплата
        3. 'family' - семейные дела, развод, алименты
        4. 'civil' - все остальные гражданские дела

        Верни ТОЛЬКО один код специализации из списка выше ('auto', 'labor', 'family', 'civil').
        Не добавляй никаких пояснений, только код.
        """

        # Используем общую модель YandexGPT для анализа
        response = yandex_client.responses.create(
            model=f"gpt://{PROJECT_ID}/yandexgpt",
            input=prompt
        )

        if hasattr(response, 'output_text') and response.output_text:
            result = response.output_text.strip().lower()

            # Проверяем, что результат - один из допустимых кодов
            valid_codes = ['auto', 'labor', 'family', 'civil']

            # Ищем код в ответе
            for code in valid_codes:
                if code in result:
                    print(f"✓ Определена специализация: {code} для проблемы: {problem_text[:50]}...")
                    return code

            # Если не нашли явно, анализируем содержание
            if 'авто' in result or 'дтп' in result or 'машин' in result:
                return 'auto'
            elif 'труд' in result or 'работа' in result or 'зарплат' in result:
                return 'labor'
            elif 'семей' in result or 'развод' in result or 'брак' in result:
                return 'family'
            else:
                return 'civil'

        return 'civil'  # По умолчанию

    except Exception as e:
        print(f"Ошибка определения специализации: {e}")
        return 'civil'  # По умолчанию при ошибке


def get_lawyer_agent_by_specialization(specialization_code):
    """Получить агента-юриста по коду специализации"""
    return AGENTS['lawyers'].get(specialization_code)


def get_all_lawyer_agents():
    """Получить всех доступных AI-юристов"""
    return AGENTS['lawyers']


def analyze_with_assistant(assistant_id, problem_text):
    """Анализ ситуации через ассистента (оставляем старую логику)"""
    try:
        response = yandex_client.responses.create(
            prompt={"id": assistant_id},
            input=problem_text
        )

        if hasattr(response, 'output_text') and response.output_text:
            output_text = response.output_text.strip()
            print(f"Ответ агента (сырой): {output_text[:200]}...")

            # ... существующий код для парсинга JSON ...
            try:
                if output_text.startswith('```json'):
                    output_text = output_text[7:]
                if output_text.endswith('```'):
                    output_text = output_text[:-3]
                output_text = output_text.strip()

                parsed_response = json.loads(output_text)
                print(f"✓ Успешно распарсен JSON")
                return parsed_response
            except json.JSONDecodeError:
                # ... существующий обработчик ошибок ...
                return {
                    "analysis": {
                        "category": "other",
                        "confidence": 0.7,
                        "summary": output_text[:200] + "..." if len(output_text) > 200 else output_text,
                        "urgency": "medium"
                    },
                    "text_response": output_text,
                    "error": "Не удалось получить структурированный ответ от агента"
                }
        else:
            print("Агент не вернул output_text")
            return {"error": "Ассистент не ответил"}

    except Exception as e:
        print(f"Ошибка при вызове API: {str(e)}")
        return {"error": str(e)}


def chat_with_lawyer(assistant_id, messages_history, chat_id=None):
    """
    Общение с AI-юристом с сохранением контекста через Conversations API

    Args:
        assistant_id: ID агента-юриста (например, 'fvt0q9er8h746fennfel' для Анны)
        messages_history: история сообщений
        chat_id: ID чата для привязки conversation
    """
    try:
        # Получаем или создаем conversation для этого чата
        conversation_id = get_or_create_conversation(chat_id) if chat_id else None

        if not conversation_id:
            print(f"⚠ Не удалось создать conversation для чата {chat_id}, пробуем старый метод")
            return chat_with_lawyer_fallback(assistant_id, messages_history)

        # Получаем последнее сообщение пользователя
        last_user_message = None
        for msg in reversed(messages_history):
            if msg['role'] == 'user':
                last_user_message = msg['content']
                break

        if not last_user_message:
            last_user_message = "Здравствуйте, нужна ваша помощь."

        # Ключевое изменение: используем prompt с ID агента, а не просто model!
        response = yandex_client.responses.create(
            prompt={"id": assistant_id},  # ← ID твоего агента Анны
            conversation=conversation_id,  # Для сохранения контекста
            input=last_user_message
        )

        if hasattr(response, 'output_text') and response.output_text:
            output_text = response.output_text.strip()
            print(f"Ответ юриста (с контекстом): {output_text[:200]}...")

            # Пробуем распарсить JSON
            try:
                # Убираем markdown коды если есть
                if output_text.startswith('```json'):
                    output_text = output_text[7:]
                if output_text.endswith('```'):
                    output_text = output_text[:-3]
                output_text = output_text.strip()

                parsed_response = json.loads(output_text)

                # Проверяем формат
                if isinstance(parsed_response, dict):
                    print(f"✓ Юрист вернул JSON: {list(parsed_response.keys())}")
                    return parsed_response

            except json.JSONDecodeError:
                print(f"Юрист не вернул JSON, возвращаем текстом")

            # Если не JSON, создаем структурированный ответ
            return {
                "lawyer_name": "Анна Ковалева",
                "specialization": "Трудовое право",
                "message": output_text,
                "questions_to_client": ["Можете рассказать подробнее о ситуации?"],
                "action_plan": ["Давайте разберем вашу ситуацию по пунктам"],
                "documents_needed": ["Все имеющиеся документы по делу"],
                "next_contact": "готов ответить сейчас"
            }
        else:
            print("Юрист не вернул ответ")
            return {"error": "Юрист не ответил"}

    except Exception as e:
        print(f"Ошибка при вызове Conversations API: {str(e)}")
        # Пробуем fallback метод
        return chat_with_lawyer_fallback(assistant_id, messages_history)


def chat_with_lawyer_fallback(assistant_id, messages_history):
    """
    Fallback метод для совместимости со старой логикой
    """
    try:
        # Получаем последнее сообщение пользователя
        last_user_message = None
        for msg in reversed(messages_history):
            if msg['role'] == 'user':
                last_user_message = msg['content']
                break

        if not last_user_message:
            last_user_message = "Здравствуйте, нужна ваша помощь."

        response = yandex_client.responses.create(
            prompt={"id": assistant_id},
            input=last_user_message
        )

        if hasattr(response, 'output_text') and response.output_text:
            output_text = response.output_text.strip()

            # ... существующий код обработки ...
            try:
                if output_text.startswith('```json'):
                    output_text = output_text[7:]
                if output_text.endswith('```'):
                    output_text = output_text[:-3]
                output_text = output_text.strip()

                parsed_response = json.loads(output_text)
                return parsed_response
            except json.JSONDecodeError:
                return {
                    "lawyer_name": "Юрист",
                    "specialization": "Правовая помощь",
                    "message": output_text,
                    "questions_to_client": ["Можете рассказать подробнее о ситуации?"],
                    "action_plan": ["Давайте разберем вашу ситуацию по пунктам"],
                    "documents_needed": ["Все имеющиеся документы по делу"],
                    "next_contact": "готов ответить сейчас"
                }
        else:
            return {"error": "Юрист не ответил"}

    except Exception as e:
        print(f"Ошибка в fallback методе: {str(e)}")
        return {"error": str(e)}