from datetime import datetime, date, timedelta, time
from django.db import transaction
from .models import Agenda, Horario

def calcular_duracao_vaga(hora_inicio: time, hora_encerramento: time, vagas: int) -> timedelta:
    """
    Calcula a duração exata entre as horas.
    """
    data_atual = date.today()
    data_inicio = datetime.combine(data_atual, hora_inicio)
    data_fim = datetime.combine(data_atual, hora_encerramento)

    duracao_total = data_fim - data_inicio
    duracao_por_vaga = duracao_total / vagas
    return duracao_por_vaga

def gerar_horarios_para_agenda(agenda: Agenda, data_inicio: date, data_fim: date) -> list[Horario]:
    """
    Gera horários para uma agenda específica entre as datas fornecidas.
    """
    if data_inicio > data_fim:
        raise ValueError("A data de início não pode ser posterior à data de fim.")

    duracao_vaga = calcular_duracao_vaga(
        agenda.hora_inicio, 
        agenda.hora_encerramento, 
        agenda.vagas_por_dia
    )

    criar_horarios = []
    data_atual = data_inicio

    while data_atual <= data_fim:
        if data_atual.weekday() in agenda.dias_semana:
            data_cursor = datetime.combine(data_atual, agenda.hora_inicio)

            for _ in range(agenda.vagas_por_dia):
                inicio_vaga = data_cursor.time()
                data_cursor += duracao_vaga
                fim_vaga = data_cursor.time()

                existe_horario = Horario.objects.filter(
                    agenda=agenda,
                    data=data_atual,
                    hora_inicio=inicio_vaga
                ).exists()

                if not existe_horario:
                    criar_horarios.append(
                        Horario(
                            agenda=agenda,
                            data=data_atual,
                            hora_inicio=inicio_vaga,
                            hora_encerramento=fim_vaga,
                            status=Horario.StatusHorario.DISPONIVEL
                        )
                    )

        data_atual += timedelta(days=1)

    with transaction.atomic():
        horarios_criados = Horario.objects.bulk_create(criar_horarios)

    return horarios_criados