from rest_framework import serializers
from .models import Usuario, Especialista, Agenda, Horario

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'tipo_acesso']

class EspecialistaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialista
        fields = ['id', 'nome', 'especialidade', 'email']


class AgendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agenda
        fields = ['id', 'especialista', 'dias_semana', 'hora_inicio', 'hora_encerramento', 'vagas_por_dia']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['especialista'] = EspecialistaSerializer(instance.especialista).data
        return representation


class HorarioSerializer(serializers.ModelSerializer):
    hora_inicio = serializers.TimeField(format='%H:%M')
    hora_encerramento = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Horario
        fields = ['id', 'agenda', 'data', 'hora_inicio', 'hora_encerramento', 'status', 'cliente']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['agenda'] = AgendaSerializer(instance.agenda).data
        if instance.cliente:
            representation['cliente'] = UsuarioSerializer(instance.cliente).data
        else:
            representation['cliente'] = None
        return representation