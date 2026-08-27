from datetime import date, time, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from consultas.models import Usuario, Especialista, Agenda, Horario
from consultas.services import gerar_horarios_para_agenda


class Command(BaseCommand):
    help = "Popula o banco de dados com usuários, especialistas, agendas e horários para testes."

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpar',
            action='store_true',
            help='Remove os dados existentes antes de popular o banco de dados.'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🌱 Iniciando o povoamento do banco de dados..."))

        if options.get('limpar'):
            self.stdout.write(self.style.WARNING("🧹 Removendo dados anteriores..."))
            Horario.all_objects.hard_delete()
            Agenda.all_objects.hard_delete()
            Especialista.all_objects.hard_delete()
            # Não remove superusuários se existirem, apenas os de teste
            Usuario.objects.filter(username__in=['admin', 'recepcao', 'paciente_joao', 'paciente_maria']).delete()
            self.stdout.write(self.style.SUCCESS("✓ Dados anteriores removidos."))

        # ---------------------------------------------------------------------
        # 1. Usuários de Demonstração
        # ---------------------------------------------------------------------
        self.stdout.write("👤 Criando usuários...")

        usuarios_dados = [
            {
                "username": "admin",
                "email": "admin@clinica.com",
                "password": "admin123",
                "tipo_acesso": Usuario.TipoAcesso.INTERNO,
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Administrador",
                "last_name": "Geral"
            },
            {
                "username": "recepcao",
                "email": "recepcao@clinica.com",
                "password": "senha123",
                "tipo_acesso": Usuario.TipoAcesso.INTERNO,
                "is_staff": True,
                "is_superuser": False,
                "first_name": "Ana",
                "last_name": "Recepção"
            },
            {
                "username": "paciente_joao",
                "email": "joao.silva@email.com",
                "password": "senha123",
                "tipo_acesso": Usuario.TipoAcesso.CLIENTE,
                "is_staff": False,
                "is_superuser": False,
                "first_name": "João",
                "last_name": "Silva"
            },
            {
                "username": "paciente_maria",
                "email": "maria.souza@email.com",
                "password": "senha123",
                "tipo_acesso": Usuario.TipoAcesso.CLIENTE,
                "is_staff": False,
                "is_superuser": False,
                "first_name": "Maria",
                "last_name": "Souza"
            }
        ]

        usuarios_criados = {}
        for dados in usuarios_dados:
            username = dados.pop("username")
            password = dados.pop("password")
            user, created = Usuario.objects.get_or_create(
                username=username,
                defaults=dados
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f"   ✓ Usuário '{username}' criado ({user.tipo_acesso}).")
            else:
                self.stdout.write(f"   - Usuário '{username}' já existia.")
            usuarios_criados[username] = user

        # ---------------------------------------------------------------------
        # 2. Especialistas
        # ---------------------------------------------------------------------
        self.stdout.write("🩺 Cadastrando especialistas...")

        especialistas_dados = [
            {
                "nome": "Dra. Ana Beatriz Silva",
                "especialidade": "Cardiologia",
                "email": "ana.silva@clinica.com"
            },
            {
                "nome": "Dr. Carlos Eduardo Santos",
                "especialidade": "Ortopedia",
                "email": "carlos.santos@clinica.com"
            },
            {
                "nome": "Dra. Mariana Costa",
                "especialidade": "Dermatologia",
                "email": "mariana.costa@clinica.com"
            },
            {
                "nome": "Dr. Lucas Fernandes",
                "especialidade": "Pediatria",
                "email": "lucas.fernandes@clinica.com"
            },
            {
                "nome": "Dra. Camila Rocha",
                "especialidade": "Ginecologia e Obstetrícia",
                "email": "camila.rocha@clinica.com"
            }
        ]

        especialistas_criados = {}
        for dados in especialistas_dados:
            email = dados["email"]
            esp, created = Especialista.objects.get_or_create(
                email=email,
                defaults={
                    "nome": dados["nome"],
                    "especialidade": dados["especialidade"],
                    "ativo": True
                }
            )
            if created:
                self.stdout.write(f"   ✓ Especialista '{esp.nome}' ({esp.especialidade}) criado.")
            else:
                self.stdout.write(f"   - Especialista '{esp.nome}' já existia.")
            especialistas_criados[email] = esp

        # ---------------------------------------------------------------------
        # 3. Agendas e Geração de Horários
        # ---------------------------------------------------------------------
        self.stdout.write("📅 Configurando agendas e gerando horários para os próximos 30 dias...")

        agendas_config = [
            {
                "especialista": especialistas_criados["ana.silva@clinica.com"],
                "dias_semana": [0, 2],  # Segundas e Quartas
                "hora_inicio": time(8, 0),
                "hora_encerramento": time(12, 0),
                "vagas_por_dia": 4  # 1h por consulta
            },
            {
                "especialista": especialistas_criados["carlos.santos@clinica.com"],
                "dias_semana": [1, 3],  # Terças e Quintas
                "hora_inicio": time(14, 0),
                "hora_encerramento": time(18, 0),
                "vagas_por_dia": 4  # 1h por consulta
            },
            {
                "especialista": especialistas_criados["mariana.costa@clinica.com"],
                "dias_semana": [0, 2, 4],  # Segundas, Quartas e Sextas
                "hora_inicio": time(9, 0),
                "hora_encerramento": time(12, 0),
                "vagas_por_dia": 3  # 1h por consulta
            },
            {
                "especialista": especialistas_criados["lucas.fernandes@clinica.com"],
                "dias_semana": [1, 4],  # Terças e Sextas
                "hora_inicio": time(8, 0),
                "hora_encerramento": time(12, 0),
                "vagas_por_dia": 4  # 1h por consulta
            },
            {
                "especialista": especialistas_criados["camila.rocha@clinica.com"],
                "dias_semana": [3, 5],  # Quintas e Sábados
                "hora_inicio": time(8, 0),
                "hora_encerramento": time(12, 0),
                "vagas_por_dia": 4  # 1h por consulta
            }
        ]

        data_inicio = date.today()
        data_fim = data_inicio + timedelta(days=30)
        total_horarios_gerados = 0

        for config in agendas_config:
            especialista = config["especialista"]
            agenda, created = Agenda.objects.get_or_create(
                especialista=especialista,
                hora_inicio=config["hora_inicio"],
                hora_encerramento=config["hora_encerramento"],
                defaults={
                    "dias_semana": config["dias_semana"],
                    "vagas_por_dia": config["vagas_por_dia"],
                    "ativo": True
                }
            )

            # Gera horários para os próximos 30 dias
            novos_horarios = gerar_horarios_para_agenda(agenda, data_inicio, data_fim)
            total_horarios_gerados += len(novos_horarios)

            if created:
                self.stdout.write(f"   ✓ Agenda criada para '{especialista.nome}' ({len(novos_horarios)} horários gerados).")
            else:
                self.stdout.write(f"   - Agenda existente para '{especialista.nome}' ({len(novos_horarios)} novos horários adicionados).")

        # ---------------------------------------------------------------------
        # 4. Agendamentos (Consultas Reservadas)
        # ---------------------------------------------------------------------
        self.stdout.write("📝 Simulando agendamentos de teste para os pacientes...")

        agora = timezone.localtime()
        data_minima = agora.date()
        hora_minima = agora.time()

        # Busca horários futuros disponíveis para agendar
        horarios_futuros_ana = Horario.objects.filter(
            agenda__especialista=especialistas_criados["ana.silva@clinica.com"],
            status=Horario.StatusHorario.DISPONIVEL,
            ativo=True,
            data__gte=data_minima
        ).exclude(data=data_minima, hora_inicio__lt=hora_minima).order_by('data', 'hora_inicio')

        horarios_futuros_carlos = Horario.objects.filter(
            agenda__especialista=especialistas_criados["carlos.santos@clinica.com"],
            status=Horario.StatusHorario.DISPONIVEL,
            ativo=True,
            data__gte=data_minima
        ).exclude(data=data_minima, hora_inicio__lt=hora_minima).order_by('data', 'hora_inicio')

        horarios_futuros_mariana = Horario.objects.filter(
            agenda__especialista=especialistas_criados["mariana.costa@clinica.com"],
            status=Horario.StatusHorario.DISPONIVEL,
            ativo=True,
            data__gte=data_minima
        ).exclude(data=data_minima, hora_inicio__lt=hora_minima).order_by('data', 'hora_inicio')

        # Agendamento 1: João com Dra. Ana Beatriz
        if horarios_futuros_ana.exists():
            h1 = horarios_futuros_ana.first()
            h1.status = Horario.StatusHorario.RESERVADO
            h1.cliente = usuarios_criados["paciente_joao"]
            h1.save()
            self.stdout.write(f"   ✓ Consulta reservada: João Silva com {h1.agenda.especialista.nome} em {h1.data.strftime('%d/%m/%Y')} às {h1.hora_inicio.strftime('%H:%M')}.")

        # Agendamento 2: João com Dr. Carlos Eduardo
        if horarios_futuros_carlos.exists():
            h2 = horarios_futuros_carlos.first()
            h2.status = Horario.StatusHorario.RESERVADO
            h2.cliente = usuarios_criados["paciente_joao"]
            h2.save()
            self.stdout.write(f"   ✓ Consulta reservada: João Silva com {h2.agenda.especialista.nome} em {h2.data.strftime('%d/%m/%Y')} às {h2.hora_inicio.strftime('%H:%M')}.")

        # Agendamento 3: Maria com Dra. Mariana Costa
        if horarios_futuros_mariana.exists():
            h3 = horarios_futuros_mariana.first()
            h3.status = Horario.StatusHorario.RESERVADO
            h3.cliente = usuarios_criados["paciente_maria"]
            h3.save()
            self.stdout.write(f"   ✓ Consulta reservada: Maria Souza com {h3.agenda.especialista.nome} em {h3.data.strftime('%d/%m/%Y')} às {h3.hora_inicio.strftime('%H:%M')}.")

        # ---------------------------------------------------------------------
        # Resumo Final
        # ---------------------------------------------------------------------
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("🎉 BANCO DE DADOS POVOADO COM SUCESSO!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"👥 Usuários criados: {Usuario.objects.count()}")
        self.stdout.write(f"🩺 Especialistas ativos: {Especialista.objects.filter(ativo=True).count()}")
        self.stdout.write(f"📅 Agendas ativas: {Agenda.objects.filter(ativo=True).count()}")
        self.stdout.write(f"⏰ Total de horários: {Horario.objects.filter(ativo=True).count()}")
        self.stdout.write(f"   - Disponíveis: {Horario.objects.filter(ativo=True, status=Horario.StatusHorario.DISPONIVEL).count()}")
        self.stdout.write(f"   - Reservados: {Horario.objects.filter(ativo=True, status=Horario.StatusHorario.RESERVADO).count()}")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.HTTP_INFO("\n🔑 Credenciais de Teste:"))
        self.stdout.write("  • Admin (Interno):     admin / admin123")
        self.stdout.write("  • Recepção (Interno):  recepcao / senha123")
        self.stdout.write("  • Paciente 1:          paciente_joao / senha123")
        self.stdout.write("  • Paciente 2:          paciente_maria / senha123\n")

