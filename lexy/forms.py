# lexy/forms.py
from django import forms
from django.core.validators import MinLengthValidator
from .models import EmergencyRequest


class EmergencyRequestForm(forms.ModelForm):
    """Форма для создания экстренного запроса"""

    class Meta:
        model = EmergencyRequest
        fields = ['problem_text']
        widgets = {
            'problem_text': forms.Textarea(attrs={
                'class': 'form-control problem-textarea',
                'placeholder': 'Например: "Попал в ДТП, виновник скрылся с места аварии", "Мне угрожают увольнением без выплаты зарплаты"...',
                'rows': 5,
                'minlength': 20,
            })
        }
        labels = {
            'problem_text': ''
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['problem_text'].validators.append(MinLengthValidator(20))

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Сохраняем техническую информацию
        if self.request:
            instance.ip_address = self.request.META.get('REMOTE_ADDR')
            instance.user_agent = self.request.META.get('HTTP_USER_AGENT', '')
            instance.session_key = self.request.session.session_key

        if commit:
            instance.save()

        return instance