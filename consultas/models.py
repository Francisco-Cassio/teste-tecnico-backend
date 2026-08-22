from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class Usuario(AbstractUser):
    class TipoAcesso(models.TextChoices):
        CLIENTE = 'cliente', 'Cliente'
        INTERNO = 'interno', 'Interno'

    tipo_acesso = models.CharField(
        max_length=20,
        choices=TipoAcesso.choices,
        default=TipoAcesso.CLIENTE
    )

    def __str__(self):
        return f"{self.username} ({self.tipo_acesso})"


class Especialista(models.Model):
    nome = models.CharField(max_length=150)
    especialidade = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.nome} - {self.especialidade}"


class Agenda(models.Model):
    especialista = models.ForeignKey(
        Especialista,
        on_delete=models.CASCADE,
        related_name='agendas'
    )

    dias_semana = models.JSONField(
        default=list,
        help_text="Lista de dias da semana (0=Segunda, 1=Terça, ..., 6=Domingo)"
    )
    hora_inicio = models.TimeField()
    hora_encerramento = models.TimeField()
    vagas_por_dia = models.PositiveIntegerField()

    def clean(self):
        if self.hora_inicio and self.hora_encerramento and self.hora_inicio >= self.hora_encerramento:
            raise ValidationError({'hora_encerramento': 'A hora de encerramento deve ser posterior à hora de início.'})
        if self.vagas_por_dia <= 0:
            raise ValidationError({'vagas_por_dia': 'A quantidade de vagas por dia deve ser maior que zero.'})

        if not isinstance(self.dias_semana, list) or len(self.dias_semana) == 0:
            raise ValidationError({'dias_semana': 'Informe ao menos um dia da semana em formato de lista.'})
        
        for dia in self.dias_semana:
            if not isinstance(dia, int) or dia < 0 or dia > 6:
                raise ValidationError({'dias_semana': f'Dia inválido: {dia}. Os valores devem ser inteiros de 0 (Segunda) a 6 (Domingo).'})

    def save(self, *args, **kwargs):    
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        nome_dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        dias = ', '.join([nome_dias[dia] for dia in self.dias_semana])

        return f"Agenda {self.especialista.nome} ({dias})"


class Horario(models.Model):
    class StatusHorario(models.TextChoices):
        DISPONIVEL = 'disponivel', 'Disponível'
        RESERVADO = 'reservado', 'Reservado'

    agenda = models.ForeignKey(
        Agenda,
        on_delete=models.CASCADE,
        related_name='horarios'
    )
    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_encerramento = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=StatusHorario.choices,
        default=StatusHorario.DISPONIVEL
    )
    cliente = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agendamentos'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['agenda', 'data', 'hora_inicio'],
                name='unique_horario_agenda_data_inicio'
            )
        ]

    def __str__(self):
        return f"{self.data} {self.hora_inicio}-{self.hora_encerramento} [{self.status}]"