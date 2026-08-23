from datetime import date, time, timedelta
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Especialista, Agenda, Horario, Usuario
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


class EndpointsAPITestCase(APITestCase):
    def setUp(self):
        # Cria um usuário de teste (cliente)
        self.cliente = Usuario.objects.create_user(
            username="paciente1",
            password="senha123",
            email="paciente@teste.com",
            tipo_acesso=Usuario.TipoAcesso.CLIENTE
        )
        # Cria um especialista de teste
        self.especialista = Especialista.objects.create(
            nome="Dr. Roberto",
            especialidade="Dermatologia",
            email="roberto@clinica.com"
        )

    # Testa a listagem de especialistas
    def test_listar_especialistas(self):
        url = reverse('especialista-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_agendar_horario(self):
    # 1. Cria uma agenda e gera horários
        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 2],  # Segunda e Quarta
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=4
        )

        gerar_horarios_para_agenda(agenda, date.today(), date.today() + timedelta(days=7))
        horario = Horario.objects.filter(agenda=agenda, status=Horario.StatusHorario.DISPONIVEL).first()
        url = reverse('horario-agendar', args=[horario.id])

        # 2. Autentica o cliente e faz a requisição para agendar o horário
        self.client.force_authenticate(user=self.cliente)
        response = self.client.post(url)

        # 3. Verifica se o horário foi agendado corretamente
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        horario.refresh_from_db()
        self.assertEqual(horario.status, Horario.StatusHorario.RESERVADO)
        self.assertEqual(horario.cliente, self.cliente)

    def test_bloquear_criacao_especialista_sem_autenticacao(self):
        # 1. Pegamos a URL do endpoint de criação de especialista
        url = reverse('especialista-list')

        # 2. Criamos o "corpo" da requisição (dados do especialista)
        dados = {
            "nome": "Dra. Juliana",
            "especialidade": "Cardiologia",
            "email": "juliana@clinica.com"
        }

        # 3. Fazemos a requisição POST sem autenticação. OBS: Não chamamos self.client.force_authenticate() aqui.
        response = self.client.post(url, dados)

        # 4. A API deve retornar 401 Unauthorized, pois o usuário não está autenticado.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bloquear_criacao_especialista_para_cliente_comum(self):
        url = reverse('especialista-list')
        dados = {
            "nome": "Dra. Juliana",
            "especialidade": "Cardiologia",
            "email": "juliana@clinica.com"
        }

        # 1. Autentica o cliente comum
        self.client.force_authenticate(user=self.cliente)

        # 2. Faz a requisição POST para criar um especialista
        response = self.client.post(url, dados)

        # 3. A API deve retornar 403 Forbidden, pois o cliente comum não tem permissão para criar especialistas.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)