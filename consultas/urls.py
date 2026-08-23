from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EspecialistaViewSet, AgendaViewSet, HorarioViewSet

router = DefaultRouter()
router.register(r'especialistas', EspecialistaViewSet, basename='especialista')
router.register(r'agendas', AgendaViewSet, basename='agenda')
router.register(r'horarios', HorarioViewSet, basename='horario')

urlpatterns = [
    path('', include(router.urls)),
]