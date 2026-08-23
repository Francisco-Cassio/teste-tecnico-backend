from rest_framework import permissions
from .models import Usuario

class IsInternoOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return bool(
            request.user and 
            request.user.is_authenticated and
            request.user.tipo_acesso == Usuario.TipoAcesso.INTERNO
        )