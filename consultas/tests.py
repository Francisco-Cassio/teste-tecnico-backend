from datetime import date, time, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Especialista, Agenda, Horario, Usuario
from .services import calcular_duracao_vaga, gerar_horarios_para_agenda


class ServicesHorariosTestCase(TestCase):
    """
    Testes unitários para a camada de serviços e regras de negócio de horários.
    """
    def setUp(self):
        self.especialista = Especialista.objects.create(
            nome="Dra. Ana Silva",
            especialidade="Cardiologia",
            email="ana.silva@clinica.com"
        )
        self.agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 2],  # Segunda e Quarta
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=4
        )

    def test_calcular_duracao_vaga(self):
        # 4 horas totais (08:00 às 12:00) / 4 vagas = 1 hora por vaga
        duracao = calcular_duracao_vaga(time(8, 0), time(12, 0), 4)
        self.assertEqual(duracao, timedelta(hours=1))

    def test_gerar_horarios_para_agenda(self):
        # Intervalo com Segunda (2026-08-24) e Quarta (2026-08-26) como dias válidos
        data_inicio = date(2026, 8, 24)  # Segunda-feira (weekday = 0)
        data_fim = date(2026, 8, 30)     # Domingo (weekday = 6)

        horarios = gerar_horarios_para_agenda(self.agenda, data_inicio, data_fim)
        # 2 dias válidos * 4 vagas = 8 horários criados
        self.assertEqual(len(horarios), 8)
        self.assertEqual(Horario.objects.count(), 8)

        # Valida se o primeiro horário começa às 08:00 e termina às 09:00 com status disponível
        primeiro_horario = Horario.objects.filter(data=data_inicio).order_by('hora_inicio').first()
        self.assertEqual(primeiro_horario.hora_inicio, time(8, 0))
        self.assertEqual(primeiro_horario.hora_encerramento, time(9, 0))
        self.assertEqual(primeiro_horario.status, Horario.StatusHorario.DISPONIVEL)

    def test_gerar_horarios_data_inicio_maior_que_data_fim(self):
        data_inicio = date(2026, 8, 30)
        data_fim = date(2026, 8, 24)
        with self.assertRaises(ValueError):
            gerar_horarios_para_agenda(self.agenda, data_inicio, data_fim)

    def test_evitar_horarios_duplicados(self):
        data_inicio = date(2026, 8, 24)
        data_fim = date(2026, 8, 30)

        gerar_horarios_para_agenda(self.agenda, data_inicio, data_fim)
        novos_horarios = gerar_horarios_para_agenda(self.agenda, data_inicio, data_fim)

        # Não deve duplicar registros no banco
        self.assertEqual(len(novos_horarios), 0)
        self.assertEqual(Horario.objects.count(), 8)


class ModelValidationTestCase(TestCase):
    """
    Testes de validação dos Models para prevenir incoerências de cadastro.
    """
    def setUp(self):
        self.especialista = Especialista.objects.create(
            nome="Dr. Carlos Eduardo",
            especialidade="Ortopedia",
            email="carlos@clinica.com"
        )

    def test_agenda_hora_encerramento_invalida(self):
        agenda = Agenda(
            especialista=self.especialista,
            dias_semana=[1, 3],
            hora_inicio=time(14, 0),
            hora_encerramento=time(10, 0),  # Menor que hora_inicio
            vagas_por_dia=4
        )
        with self.assertRaises(ValidationError):
            agenda.full_clean()

    def test_agenda_vagas_por_dia_zerada_ou_negativa(self):
        agenda = Agenda(
            especialista=self.especialista,
            dias_semana=[1, 3],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=0
        )
        with self.assertRaises(ValidationError):
            agenda.full_clean()

    def test_agenda_dias_semana_vazio_ou_invalido(self):
        # Lista vazia
        agenda_vazia = Agenda(
            especialista=self.especialista,
            dias_semana=[],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=2
        )
        with self.assertRaises(ValidationError):
            agenda_vazia.full_clean()

        # Dia fora do intervalo 0 a 6 (ex: 7)
        agenda_dia_invalido = Agenda(
            especialista=self.especialista,
            dias_semana=[0, 7],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=2
        )
        with self.assertRaises(ValidationError):
            agenda_dia_invalido.full_clean()

    def test_str_representations(self):
        usuario = Usuario(username="joao", tipo_acesso=Usuario.TipoAcesso.CLIENTE)
        self.assertEqual(str(usuario), "joao (cliente)")

        self.assertEqual(str(self.especialista), "Dr. Carlos Eduardo - Ortopedia")

        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 4],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=2
        )
        self.assertIn("Agenda Dr. Carlos Eduardo", str(agenda))


class AutenticacaoEPerfisAPITestCase(APITestCase):
    """
    Testes de autenticação JWT e controle de permissões por perfil (Interno vs Cliente).
    """
    def setUp(self):
        self.senha_padrao = "senhaForte123"
        self.usuario_cliente = Usuario.objects.create_user(
            username="cliente_teste",
            password=self.senha_padrao,
            email="cliente@teste.com",
            tipo_acesso=Usuario.TipoAcesso.CLIENTE
        )
        self.usuario_interno = Usuario.objects.create_user(
            username="interno_teste",
            password=self.senha_padrao,
            email="interno@clinica.com",
            tipo_acesso=Usuario.TipoAcesso.INTERNO
        )

    def test_obter_token_jwt_sucesso(self):
        url = reverse('token_obtain_pair')
        dados = {
            "username": "cliente_teste",
            "password": self.senha_padrao
        }
        response = self.client.post(url, dados, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_obter_token_jwt_credenciais_invalidas(self):
        url = reverse('token_obtain_pair')
        dados = {
            "username": "cliente_teste",
            "password": "senhaErrada"
        }
        response = self.client.post(url, dados, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bloquear_criacao_especialista_sem_autenticacao(self):
        url = reverse('especialista-list')
        dados = {
            "nome": "Dra. Juliana",
            "especialidade": "Cardiologia",
            "email": "juliana@clinica.com"
        }
        response = self.client.post(url, dados, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bloquear_criacao_especialista_para_cliente(self):
        url = reverse('especialista-list')
        dados = {
            "nome": "Dra. Juliana",
            "especialidade": "Cardiologia",
            "email": "juliana@clinica.com"
        }
        self.client.force_authenticate(user=self.usuario_cliente)
        response = self.client.post(url, dados, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permitir_criacao_especialista_para_usuario_interno(self):
        url = reverse('especialista-list')
        dados = {
            "nome": "Dra. Juliana",
            "especialidade": "Cardiologia",
            "email": "juliana@clinica.com"
        }
        self.client.force_authenticate(user=self.usuario_interno)
        response = self.client.post(url, dados, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Especialista.objects.filter(email="juliana@clinica.com").count(), 1)


class ConsultasEAgendamentosAPITestCase(APITestCase):
    """
    Testes de integração para os fluxos da API de especialistas, agendas e agendamento de horários.
    """
    def setUp(self):
        self.cliente = Usuario.objects.create_user(
            username="paciente_agendamento",
            password="123",
            email="paciente@clinica.com",
            tipo_acesso=Usuario.TipoAcesso.CLIENTE
        )
        self.interno = Usuario.objects.create_user(
            username="secretaria_interno",
            password="123",
            email="secretaria@clinica.com",
            tipo_acesso=Usuario.TipoAcesso.INTERNO
        )
        self.especialista = Especialista.objects.create(
            nome="Dr. Roberto",
            especialidade="Dermatologia",
            email="roberto@clinica.com"
        )

    def test_listar_especialistas_publicamente(self):
        url = reverse('especialista-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count = response.data['count'] if isinstance(response.data, dict) and 'count' in response.data else len(response.data)
        self.assertEqual(count, 1)

    def test_criar_agenda_via_api_gera_horarios_automaticamente(self):
        url = reverse('agenda-list')
        dados_agenda = {
            "especialista": self.especialista.id,
            "dias_semana": [0, 2],  # Segundas e Quartas
            "hora_inicio": "08:00",
            "hora_encerramento": "12:00",
            "vagas_por_dia": 4
        }
        self.client.force_authenticate(user=self.interno)
        response = self.client.post(url, dados_agenda, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        agenda_criada = Agenda.objects.get(id=response.data['id'])
        self.assertTrue(Horario.objects.filter(agenda=agenda_criada).exists())

    def test_bloquear_criacao_agenda_por_cliente(self):
        url = reverse('agenda-list')
        dados_agenda = {
            "especialista": self.especialista.id,
            "dias_semana": [0, 2],
            "hora_inicio": "08:00",
            "hora_encerramento": "12:00",
            "vagas_por_dia": 4
        }
        self.client.force_authenticate(user=self.cliente)
        response = self.client.post(url, dados_agenda, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agendar_horario_disponivel_com_sucesso(self):
        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=4
        )
        horario = Horario.objects.create(
            agenda=agenda,
            data=date.today() + timedelta(days=1),  # Horário futuro
            hora_inicio=time(8, 0),
            hora_encerramento=time(9, 0),
            status=Horario.StatusHorario.DISPONIVEL
        )

        url = reverse('horario-agendar', args=[horario.id])
        self.client.force_authenticate(user=self.cliente)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        horario.refresh_from_db()
        self.assertEqual(horario.status, Horario.StatusHorario.RESERVADO)
        self.assertEqual(horario.cliente, self.cliente)

    def test_bloquear_agendamento_de_horario_ja_reservado(self):
        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=4
        )
        horario = Horario.objects.create(
            agenda=agenda,
            data=date.today() + timedelta(days=1),
            hora_inicio=time(8, 0),
            hora_encerramento=time(9, 0),
            status=Horario.StatusHorario.RESERVADO,
            cliente=self.cliente
        )

        outro_cliente = Usuario.objects.create_user(
            username="outro_paciente",
            password="123",
            tipo_acesso=Usuario.TipoAcesso.CLIENTE
        )

        url = reverse('horario-agendar', args=[horario.id])
        self.client.force_authenticate(user=outro_cliente)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Horário não disponível para agendamento.")

    def test_bloquear_agendamento_em_data_passada(self):
        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=4
        )
        horario_ontem = Horario.objects.create(
            agenda=agenda,
            data=date.today() - timedelta(days=1),  # 👈 Ontem
            hora_inicio=time(8, 0),
            hora_encerramento=time(9, 0),
            status=Horario.StatusHorario.DISPONIVEL
        )
        url = reverse('horario-agendar', args=[horario_ontem.id])
        self.client.force_authenticate(user=self.cliente)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("passados", response.data['detail'])

    def test_bloquear_agendamento_sem_autenticacao(self):
        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=4
        )
        horario = Horario.objects.create(
            agenda=agenda,
            data=date.today(),
            hora_inicio=time(8, 0),
            hora_encerramento=time(9, 0),
            status=Horario.StatusHorario.DISPONIVEL
        )

        url = reverse('horario-agendar', args=[horario.id])
        # Requisição sem autenticação
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_agendar_horario_inexistente(self):
        url = reverse('horario-agendar', args=[999999])
        self.client.force_authenticate(user=self.cliente)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filtrar_horarios_por_especialista_data_e_status(self):
        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=2
        )
        data_hoje = date.today()
        h1 = Horario.objects.create(
            agenda=agenda,
            data=data_hoje,
            hora_inicio=time(8, 0),
            hora_encerramento=time(10, 0),
            status=Horario.StatusHorario.DISPONIVEL
        )
        h2 = Horario.objects.create(
            agenda=agenda,
            data=data_hoje,
            hora_inicio=time(10, 0),
            hora_encerramento=time(12, 0),
            status=Horario.StatusHorario.RESERVADO,
            cliente=self.cliente
        )

        url = reverse('horario-list')

        # Filtro por status disponível
        res_status = self.client.get(url, {'status': 'disponivel'})
        self.assertEqual(res_status.status_code, status.HTTP_200_OK)
        results = res_status.data['results'] if 'results' in res_status.data else res_status.data
        self.assertTrue(all(item['status'] == 'disponivel' for item in results))

        # Filtro por especialista_id
        res_esp = self.client.get(url, {'especialista_id': self.especialista.id})
        self.assertEqual(res_esp.status_code, status.HTTP_200_OK)
        results_esp = res_esp.data['results'] if 'results' in res_esp.data else res_esp.data
        self.assertTrue(len(results_esp) >= 2)

        # Filtro por data
        res_data = self.client.get(url, {'data_consulta': data_hoje.isoformat()})
        self.assertEqual(res_data.status_code, status.HTTP_200_OK)
        results_data = res_data.data['results'] if 'results' in res_data.data else res_data.data
        self.assertTrue(all(item['data'] == data_hoje.isoformat() for item in results_data))

    def test_soft_delete_especialista(self):
        url = reverse('especialista-detail', args=[self.especialista.id])
        self.client.force_authenticate(user=self.interno)
        
        # 1. Faz a requisição de exclusão na API
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 2. Na API / listagem padrão (objects), o especialista não aparece mais
        self.assertFalse(Especialista.objects.filter(id=self.especialista.id).exists())

        # 3. No banco de dados (all_objects), o registro continua existindo com ativo=False
        especialista_inativo = Especialista.all_objects.get(id=self.especialista.id)
        self.assertFalse(especialista_inativo.ativo)

    def test_soft_delete_agenda_inativa_horarios_disponiveis(self):
        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=2
        )
        horario = Horario.objects.create(
            agenda=agenda,
            data=date.today() + timedelta(days=1),
            hora_inicio=time(8, 0),
            hora_encerramento=time(10, 0),
            status=Horario.StatusHorario.DISPONIVEL
        )
        
        url = reverse('agenda-detail', args=[agenda.id])
        self.client.force_authenticate(user=self.interno)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Agenda e horário disponível somem da consulta padrão
        self.assertFalse(Agenda.objects.filter(id=agenda.id).exists())
        self.assertFalse(Horario.objects.filter(id=horario.id).exists())

        # Mas permanecem no banco para auditoria com ativo=False
        self.assertFalse(Agenda.all_objects.get(id=agenda.id).ativo)
        self.assertFalse(Horario.all_objects.get(id=horario.id).ativo)

    def test_cancelar_agendamento_proprio(self):
        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=4
        )
        horario = Horario.objects.create(
            agenda=agenda,
            data=date.today() + timedelta(days=2),
            hora_inicio=time(8, 0),
            hora_encerramento=time(9, 0),
            status=Horario.StatusHorario.RESERVADO,
            cliente=self.cliente
        )
        url = reverse('horario-cancelar', args=[horario.id])
        self.client.force_authenticate(user=self.cliente)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        horario.refresh_from_db()
        self.assertEqual(horario.status, Horario.StatusHorario.DISPONIVEL)
        self.assertIsNone(horario.cliente)

    def test_bloquear_cancelamento_de_consulta_de_outro_cliente(self):
        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=4
        )
        horario = Horario.objects.create(
            agenda=agenda,
            data=date.today() + timedelta(days=2),
            hora_inicio=time(8, 0),
            hora_encerramento=time(9, 0),
            status=Horario.StatusHorario.RESERVADO,
            cliente=self.cliente
        )
        outro_cliente = Usuario.objects.create_user(
            username="outro_paciente_cancelar",
            password="123",
            tipo_acesso=Usuario.TipoAcesso.CLIENTE
        )
        url = reverse('horario-cancelar', args=[horario.id])
        self.client.force_authenticate(user=outro_cliente)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_usuario_interno_pode_cancelar_consulta_de_qualquer_cliente(self):
        agenda = Agenda.objects.create(
            especialista=self.especialista,
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            hora_inicio=time(8, 0),
            hora_encerramento=time(12, 0),
            vagas_por_dia=4
        )
        horario = Horario.objects.create(
            agenda=agenda,
            data=date.today() + timedelta(days=2),
            hora_inicio=time(8, 0),
            hora_encerramento=time(9, 0),
            status=Horario.StatusHorario.RESERVADO,
            cliente=self.cliente
        )
        url = reverse('horario-cancelar', args=[horario.id])
        self.client.force_authenticate(user=self.interno)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        horario.refresh_from_db()
        self.assertEqual(horario.status, Horario.StatusHorario.DISPONIVEL)
        self.assertIsNone(horario.cliente)


class ConfiguracoesGlobaisTestCase(APITestCase):
    """
    Testes para configurações gerais do projeto (CORS e Django Admin).
    """
    def test_cors_headers_habilitados(self):
        url = reverse('especialista-list')
        response = self.client.get(url, HTTP_ORIGIN='http://localhost:5173')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access-control-allow-origin', response.headers)

    def test_admin_telas_carregam_com_sucesso(self):
        super_user = Usuario.objects.create_superuser(
            username='admin_master',
            email='admin@master.com',
            password='123'
        )
        self.client.force_login(super_user)
        
        rotas_admin = [
            'admin:consultas_usuario_changelist',
            'admin:consultas_especialista_changelist',
            'admin:consultas_agenda_changelist',
            'admin:consultas_horario_changelist',
        ]
        for rota in rotas_admin:
            res = self.client.get(reverse(rota))
            self.assertEqual(res.status_code, status.HTTP_200_OK)