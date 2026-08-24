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

    def validate(self, attrs):
        hora_inicio = attrs.get('hora_inicio', getattr(self.instance, 'hora_inicio', None))
        hora_encerramento = attrs.get('hora_encerramento', getattr(self.instance, 'hora_encerramento', None))
        vagas_por_dia = attrs.get('vagas_por_dia', getattr(self.instance, 'vagas_por_dia', None))
        dias_semana = attrs.get('dias_semana', getattr(self.instance, 'dias_semana', None))

        if hora_inicio and hora_encerramento and hora_inicio >= hora_encerramento:
            raise serializers.ValidationError({
                'hora_encerramento': 'A hora de encerramento deve ser posterior à hora de início.'
            })

        if vagas_por_dia is not None and vagas_por_dia <= 0:
            raise serializers.ValidationError({
                'vagas_por_dia': 'A quantidade de vagas por dia deve ser maior que zero.'
            })

        if dias_semana is not None:
            if not isinstance(dias_semana, list) or len(dias_semana) == 0:
                raise serializers.ValidationError({
                    'dias_semana': 'Informe ao menos um dia da semana em formato de lista.'
                })
            for dia in dias_semana:
                if not isinstance(dia, int) or dia < 0 or dia > 6:
                    raise serializers.ValidationError({
                        'dias_semana': f'Dia inválido: {dia}. Os valores devem ser inteiros de 0 (Segunda) a 6 (Domingo).'
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