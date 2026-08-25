from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Especialista, Agenda, Horario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'tipo_acesso', 'is_staff', 'is_active')
    list_filter = ('tipo_acesso', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Informações de Acesso', {'fields': ('tipo_acesso',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informações de Acesso', {'fields': ('tipo_acesso',)}),
    )


@admin.register(Especialista)
class EspecialistaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'especialidade', 'email', 'ativo')
    search_fields = ('nome', 'especialidade', 'email')
    list_filter = ('especialidade', 'ativo')

    def get_queryset(self, request):
        return Especialista.all_objects.all()


@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'especialista', 'hora_inicio', 'hora_encerramento', 'vagas_por_dia', 'ativo')
    search_fields = ('especialista__nome', 'especialista__especialidade')
    list_filter = ('especialista', 'ativo')

    def get_queryset(self, request):
        return Agenda.all_objects.all()


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_especialista', 'data', 'hora_inicio', 'hora_encerramento', 'status', 'cliente', 'ativo')
    list_filter = ('status', 'data', 'agenda__especialista', 'ativo')
    search_fields = ('agenda__especialista__nome', 'cliente__username')
    ordering = ('data', 'hora_inicio')

    def get_queryset(self, request):
        return Horario.all_objects.all()

    @admin.display(description='Especialista')
    def get_especialista(self, obj):
        return obj.agenda.especialista.nome