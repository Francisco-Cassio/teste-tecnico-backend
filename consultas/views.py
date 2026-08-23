from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Usuario, Especialista, Agenda, Horario
from .serializers import UsuarioSerializer, EspecialistaSerializer, AgendaSerializer, HorarioSerializer
from .services import gerar_horarios_para_agenda
from django.db import transaction
from datetime import date, timedelta

class EspecialistaViewSet(viewsets.ModelViewSet):
    queryset = Especialista.objects.all()
    serializer_class = EspecialistaSerializer

class AgendaViewSet(viewsets.ModelViewSet):
    queryset = Agenda.objects.all()
    serializer_class = AgendaSerializer

    def perform_create(self, serializer):
        agenda = serializer.save()
        data_inicio = date.today()
        data_fim = data_inicio + timedelta(days=30)
        gerar_horarios_para_agenda(agenda, data_inicio, data_fim)

class HorarioViewSet(viewsets.ModelViewSet):
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        especialista_id = self.request.query_params.get('especialista_id')
        data_consulta = self.request.query_params.get('data_consulta')
        status = self.request.query_params.get('status')

        if especialista_id:
            queryset = queryset.filter(agenda__especialista_id=especialista_id)

        if data_consulta:
            queryset = queryset.filter(data=data_consulta)

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def agendar(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({"detail": "É necessário estar autenticado para agendar."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            horario = Horario.objects.select_for_update().get(pk=pk)
        except Horario.DoesNotExist:
            return Response({"detail": "Horário não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if horario.status != Horario.StatusHorario.DISPONIVEL:
            return Response({"detail": "Horário não disponível para agendamento."}, status=status.HTTP_400_BAD_REQUEST)

        horario.status = Horario.StatusHorario.RESERVADO
        horario.cliente = request.user
        horario.save()

        serializer = self.get_serializer(horario)

        return Response(serializer.data, status=status.HTTP_200_OK)