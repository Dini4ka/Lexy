# lexy_core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('lexy.urls')),
    path('how-it-works/', TemplateView.as_view(template_name='lexy/how_it_works.html'), name='how_it_works'),
    path('privacy/', TemplateView.as_view(template_name='lexy/privacy.html'), name='privacy'),
    path('terms/', TemplateView.as_view(template_name='lexy/terms.html'), name='terms'),
]

# Добавляем обработку статических файлов в development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)