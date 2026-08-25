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
    dias_semana = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        allow_empty=False,
        help_text="Lista de dias da semana (0=Segunda, 1=Terça, ..., 6=Domingo)"
    )

    class Meta:
        model = Agenda
        fields = ['id', 'especialista', 'dias_semana', 'hora_inicio', 'hora_encerramento', 'vagas_por_dia']

    def validate(self, attrs):
        hora_inicio = attrs.get('hora_inicio', getattr(self.instance, 'hora_inicio', None))
        hora_encerramento = attrs.get('hora_encerramento', getattr(self.instance, 'hora_encerramento', None))
        vagas_por_dia = attrs.get('vagas_por_dia', getattr(self.instance, 'vagas_por_dia', None))

        if hora_inicio and hora_encerramento and hora_inicio >= hora_encerramento:
            raise serializers.ValidationError({
                'hora_encerramento': 'A hora de encerramento deve ser posterior à hora de início.'
            })

        if vagas_por_dia is not None and vagas_por_dia <= 0:
            raise serializers.ValidationError({
                'vagas_por_dia': 'A quantidade de vagas por dia deve ser maior que zero.'
            })

        return attrs

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