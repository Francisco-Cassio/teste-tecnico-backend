from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(ativo=False)
    
    def hard_delete(self):
        return super().delete()
    
    def ativos(self):
        return self.filter(ativo=True)
        
    def inativos(self):
        return self.filter(ativo=False)


class SoftDeleteManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.apenas_ativos = kwargs.pop('apenas_ativos', True)
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        if self.apenas_ativos:
            return SoftDeleteQuerySet(self.model, using=self._db).filter(ativo=True)
        return SoftDeleteQuerySet(self.model, using=self._db)

    def hard_delete(self):
        return self.get_queryset().hard_delete()


class SoftDeleteModel(models.Model):
    ativo = models.BooleanField(default=True, db_index=True)
    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(apenas_ativos=False)
    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.ativo = False
        self.save(using=using, update_fields=['ativo'])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

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


class Especialista(SoftDeleteModel):
    nome = models.CharField(max_length=150)
    especialidade = models.CharField(max_length=100)
    email = models.EmailField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['email'],
                condition=models.Q(ativo=True),
                name='unique_active_especialista_email'
            )
        ]

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)
        for agenda in self.agendas.filter(ativo=True):
            agenda.delete(using=using)

    def __str__(self):
        return f"{self.nome} - {self.especialidade}"


class Agenda(SoftDeleteModel):
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
        if self.vagas_por_dia is not None and self.vagas_por_dia <= 0:
            raise ValidationError({'vagas_por_dia': 'A quantidade de vagas por dia deve ser maior que zero.'})

        if not isinstance(self.dias_semana, list) or len(self.dias_semana) == 0:
            raise ValidationError({'dias_semana': 'Informe ao menos um dia da semana em formato de lista.'})
        
        for dia in self.dias_semana:
            if not isinstance(dia, int) or dia < 0 or dia > 6:
                raise ValidationError({'dias_semana': f'Dia inválido: {dia}. Os valores devem ser inteiros de 0 (Segunda) a 6 (Domingo).'})

    def save(self, *args, **kwargs):    
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)
        self.horarios.filter(status=Horario.StatusHorario.DISPONIVEL, ativo=True).delete()

    def __str__(self):
        nome_dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        dias = ', '.join([nome_dias[dia] for dia in self.dias_semana])
        return f"Agenda {self.especialista.nome} ({dias})"


class Horario(SoftDeleteModel):
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
                condition=models.Q(ativo=True),
                name='unique_active_horario_agenda_data_inicio'
            )
        ]

    def __str__(self):
        return f"{self.data} {self.hora_inicio}-{self.hora_encerramento} [{self.status}]"