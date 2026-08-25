from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
    
from .models import Especialista, Agenda, Horario
from .serializers import EspecialistaSerializer, AgendaSerializer, HorarioSerializer
from .permissions import IsInternoOrReadOnly
from .services import gerar_horarios_para_agenda

@extend_schema_view(
    list=extend_schema(summary="Listar especialistas", description="Retorna a lista de especialistas cadastrados."),
    create=extend_schema(summary="Cadastrar especialista", description="Cadastra um novo especialista. Requer perfil Interno."),
    retrieve=extend_schema(summary="Detalhar especialista", description="Retorna os detalhes de um especialista específico."),
    update=extend_schema(summary="Atualizar especialista", description="Atualiza todos os dados de um especialista. Requer perfil Interno."),
    partial_update=extend_schema(summary="Atualizar parcialmente especialista", description="Atualiza campos de um especialista. Requer perfil Interno."),
    destroy=extend_schema(summary="Excluir especialista", description="Remove um especialista cadastrado. Requer perfil Interno."),
)


class EspecialistaViewSet(viewsets.ModelViewSet):
    queryset = Especialista.objects.all()
    serializer_class = EspecialistaSerializer
    permission_classes = [IsInternoOrReadOnly]

@extend_schema_view(
    list=extend_schema(summary="Listar agendas", description="Retorna a lista de agendas de atendimento."),
    create=extend_schema(summary="Criar agenda", description="Cria uma agenda para um especialista e gera automaticamente os horários de atendimento para os próximos 30 dias. Requer perfil Interno."),
    retrieve=extend_schema(summary="Detalhar agenda", description="Retorna os detalhes de uma agenda."),
    update=extend_schema(summary="Atualizar agenda", description="Atualiza os dados de uma agenda. Requer perfil Interno."),
    partial_update=extend_schema(summary="Atualizar parcialmente agenda", description="Atualiza campos de uma agenda. Requer perfil Interno."),
    destroy=extend_schema(summary="Excluir agenda", description="Remove uma agenda. Requer perfil Interno."),
)


class AgendaViewSet(viewsets.ModelViewSet):
    queryset = Agenda.objects.select_related('especialista').all()
    serializer_class = AgendaSerializer
    permission_classes = [IsInternoOrReadOnly]

    @transaction.atomic
    def perform_create(self, serializer):
        agenda = serializer.save()
        data_inicio = date.today()
        data_fim = data_inicio + timedelta(days=30)
        gerar_horarios_para_agenda(agenda, data_inicio, data_fim)

@extend_schema_view(
    list=extend_schema(
        summary="Listar horários de consulta",
        description="Retorna a lista de horários de atendimento gerados. Permite filtrar por especialista, data da consulta e status.",
        parameters=[
            OpenApiParameter(name='especialista_id', description='ID do especialista para filtrar horários', required=False, type=OpenApiTypes.INT),
            OpenApiParameter(name='data_consulta', description='Data da consulta (AAAA-MM-DD)', required=False, type=OpenApiTypes.DATE),
            OpenApiParameter(name='status', description='Status do horário (disponivel ou reservado)', required=False, type=OpenApiTypes.STR),
        ]
    ),
    retrieve=extend_schema(summary="Detalhar horário", description="Retorna detalhes de um horário de consulta."),
    create=extend_schema(summary="Criar horário manualmente", description="Cria um horário de consulta manualmente. Requer perfil Interno."),
    update=extend_schema(summary="Atualizar horário", description="Atualiza um horário. Requer perfil Interno."),
    partial_update=extend_schema(summary="Atualizar parcialmente horário", description="Atualiza campos de um horário. Requer perfil Interno."),
    destroy=extend_schema(summary="Excluir horário", description="Exclui um horário de consulta. Requer perfil Interno."),
)


class HorarioViewSet(viewsets.ModelViewSet):
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer
    permission_classes = [IsInternoOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset().select_related('agenda', 'agenda__especialista', 'cliente')

        especialista_id = self.request.query_params.get('especialista_id')
        data_consulta = self.request.query_params.get('data_consulta')
        status_param = self.request.query_params.get('status')

        if especialista_id:
            queryset = queryset.filter(agenda__especialista_id=especialista_id)

        if data_consulta:
            queryset = queryset.filter(data=data_consulta)

        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset

    @extend_schema(
        summary="Agendar consulta",
        description="Reserva um horário de consulta disponível para o usuário cliente autenticado.",
        request=None,
        responses={200: HorarioSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def agendar(self, request, pk=None):
        try:
            horario = (
                Horario.objects
                .select_for_update()
                .select_related('agenda', 'agenda__especialista')
                .get(pk=pk)
            )
        except Horario.DoesNotExist:
            return Response({"detail": "Horário não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if horario.status != Horario.StatusHorario.DISPONIVEL:
            return Response({"detail": "Horário não disponível para agendamento."}, status=status.HTTP_400_BAD_REQUEST)

        agora = timezone.localtime()
        data_atual = agora.date()
        horario_data = agora.time()
        
        if horario.data < data_atual or (horario.data == data_atual and horario.hora_inicio < horario_data):
            return Response({"detail": "Não é possível agendar horários passados."}, status=status.HTTP_400_BAD_REQUEST)

        horario.status = Horario.StatusHorario.RESERVADO
        horario.cliente = request.user
        horario.save()

        serializer = self.get_serializer(horario)

        return Response(serializer.data, status=status.HTTP_200_OK)