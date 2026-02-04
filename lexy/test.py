# В Python shell проверь
from lexy.yandex_utils import analyze_with_assistant

# Протестируй общего агента
test_response = analyze_with_assistant('fvt0q9er8h746fennfel', 'Как тебя зовут и расскажи о себе')
print(test_response)

# Проверь, что это JSON
import json
if isinstance(test_response, dict):
    print("✓ Агент возвращает JSON")
    print(json.dumps(test_response, indent=2, ensure_ascii=False))