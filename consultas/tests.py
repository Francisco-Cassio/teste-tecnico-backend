from datetime import date, time, timedelta
from django.test import TestCase
from .models import Especialista, Agenda, Horario
from .services import calcular_duracao_vaga, gerar_horarios_para_agenda


class ServicesHorariosTestCase(TestCase):
    def setUp(self):
        # Cria um especialista para os testes
        self.especialista = Especialista.objects.create(
            nome="Dra. Ana Silva",
            especialidade="Cardiologia",
            email="ana.silva@clinica.com"
        )
        # Cria uma agenda: Segundas e Quartas (0 e 2), das 08:00 às 12:00, com 4 vagas
        self.agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 2],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=4
        )

    def test_calcular_duracao_vaga(self):
        # Total de 4 vagas entre 08:00 e 12:00 => 4 horas / 4 vagas = 1 hora por vaga
        duracao = calcular_duracao_vaga(time(8, 0), time(12, 0), 4)
        self.assertEqual(duracao, timedelta(hours=1))

    def test_gerar_horarios_para_agenda(self):
        # Intervalo de uma semana com Segunda (2026-08-24) e Quarta (2026-08-26) como dias válidos
        data_inicio = date(2026, 8, 24)  # Segunda-feira (weekday = 0)
        data_fim = date(2026, 8, 30)     # Domingo (weekday = 6)

        horarios = gerar_horarios_para_agenda(self.agenda, data_inicio, data_fim)
        # 2 dias válidos * 4 vagas = 8 horários criados

        self.assertEqual(len(horarios), 8)
        self.assertEqual(Horario.objects.count(), 8)

        # Valida se o primeiro horário começa às 08:00 e termina às 09:00
        primeiro_horario = Horario.objects.filter(data=data_inicio).order_by('hora_inicio').first()
        self.assertEqual(primeiro_horario.hora_inicio, time(8, 0))
        self.assertEqual(primeiro_horario.hora_encerramento, time(9, 0))
        self.assertEqual(primeiro_horario.status, Horario.StatusHorario.DISPONIVEL)

    def test_evitar_horarios_duplicados(self):
        data_inicio = date(2026, 8, 24)
        data_fim = date(2026, 8, 30)

        # Executa a geração pela primeira vez
        gerar_horarios_para_agenda(self.agenda, data_inicio, data_fim)
        # Executa a segunda vez para o mesmo período
        novos_horarios = gerar_horarios_para_agenda(self.agenda, data_inicio, data_fim)

        # Não deve duplicar registros no banco
        self.assertEqual(len(novos_horarios), 0)
        self.assertEqual(Horario.objects.count(), 8)