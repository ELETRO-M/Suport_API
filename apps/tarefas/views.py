from typing import cast

from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.configuracoes.responses import resposta_sucesso as resposta_view
from apps.configuracoes.schema import (
    resposta_criar,
    resposta_eliminar,
    resposta_erro,
    resposta_sucesso,
)
from apps.tarefas.models import AnexoTarefa, ComentarioTarefa, Tarefa
from apps.tarefas.serializers import (
    AdicionarComentarioSerializer,
    AnexoResumoSerializer,
    AtribuirRespostaSerializer,
    AtribuirTarefaSerializer,
    CarregarAnexoSerializer,
    ComentarioResumoSerializer,
    ComentarioTarefaSerializer,
    TarefaCriadaSerializer,
    TarefaDetalheSerializer,
    TarefaEscritaSerializer,
    TarefaListaSerializer,
)
from apps.usuarios.models import Usuario


filtro_estado = OpenApiParameter(
    name="estado",
    description="Filtra pelo estado da tarefa.",
    required=False,
    enum=["pendente", "em_progresso", "concluida", "cancelada", "expirado"],
)
filtro_prioridade = OpenApiParameter(
    name="prioridade",
    description="Filtra pela prioridade da tarefa.",
    required=False,
    enum=["baixa", "media", "alta", "urgente"],
)


@extend_schema(tags=["Tarefas"])
class TarefaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]
    serializer_action_classes = {
        "retrieve": TarefaDetalheSerializer,
        "create": TarefaEscritaSerializer,
        "update": TarefaEscritaSerializer,
        "partial_update": TarefaEscritaSerializer,
        "atribuir": AtribuirTarefaSerializer,
        "comentarios": AdicionarComentarioSerializer,
        "anexos": CarregarAnexoSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_action_classes.get(self.action, TarefaListaSerializer)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Tarefa.objects.none()
        request = cast(Request, self.request)
        queryset = Tarefa.objects.select_related("atribuido_a", "criado_por", "intervencao").prefetch_related(
            "comentarios",
            "anexos",
        )
        params = request.query_params
        if params.get("estado"):
            queryset = queryset.filter(estado=params["estado"])
        if params.get("prioridade"):
            queryset = queryset.filter(prioridade=params["prioridade"])
        if params.get("atribuido_a_id"):
            queryset = queryset.filter(atribuido_a_id=params["atribuido_a_id"])
        if params.get("intervencao_id"):
            queryset = queryset.filter(intervencao_id=params["intervencao_id"])

        utilizador = request.user
        if utilizador.perfil == Usuario.PerfilChoices.TECNICO:
            queryset = queryset.filter(atribuido_a=utilizador)
        elif utilizador.perfil == Usuario.PerfilChoices.CLIENTE:
            return Tarefa.objects.none()
        queryset.filter(
            data_fim__lte=timezone.now(),
            estado__in=[Tarefa.EstadoChoices.PENDENTE, Tarefa.EstadoChoices.EM_PROGRESSO],
        ).update(estado=Tarefa.EstadoChoices.EXPIRADO)
        return queryset

    @extend_schema(
        summary="Listar tarefas",
        operation_id="tarefas_lista",
        description=(
            "Lista as tarefas com paginação (10 por página; use `?page=N`). "
            "Tarefas `pendente`/`em_progresso` cujo prazo já passou são marcadas como `expirado` automaticamente. "
            "O **técnico** vê apenas as tarefas que lhe estão atribuídas; o **cliente** não acede."
        ),
        parameters=[filtro_estado, filtro_prioridade],
        responses={
            200: resposta_sucesso(
                TarefaListaSerializer(many=True),
                "Lista de tarefas.",
                "TarefaLista",
            ),
            401: resposta_erro("Autenticação necessária."),
        },
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return resposta_view(data=serializer.data)

    @extend_schema(
        summary="Detalhes de uma tarefa",
        operation_id="tarefas_detalhe",
        description="Devolve os dados completos de uma tarefa, incluindo comentários e anexos.",
        responses={
            200: resposta_sucesso(
                TarefaDetalheSerializer,
                "Detalhes da tarefa.",
                "TarefaDetalhe",
            ),
            401: resposta_erro("Autenticação necessária."),
            404: resposta_erro("Tarefa não encontrada ou sem permissão."),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, context={"request": request})
        return resposta_view(data=serializer.data)

    @extend_schema(
        summary="Criar tarefa",
        operation_id="tarefas_criar",
        description=(
            "Cria uma nova tarefa. **Apenas administradores.** "
            "Se `data_fim` for no passado, a tarefa nasce com estado `expirado`. "
            "Se for atribuída no momento da criação, o responsável é notificado (app + WhatsApp)."
        ),
        request=TarefaEscritaSerializer,
        responses={
            201: resposta_criar(
                TarefaCriadaSerializer,
                "Tarefa criada.",
                "Tarefa",
                exemplos=[
                    OpenApiExample(
                        "Exemplo",
                        value={"id": "uuid", "numero": "TAR-2026-001", "estado": "pendente"},
                    )
                ],
            ),
            403: resposta_erro("Apenas administradores podem criar tarefas."),
            400: resposta_erro("Dados inválidos."),
        },
    )
    def create(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem criar tarefas.")
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(criado_por=request.user)
        return resposta_view(
            data={"id": str(obj.id), "numero": obj.numero, "estado": obj.estado},
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Atualizar tarefa",
        operation_id="tarefas_atualizar",
        description=(
            "Atualiza uma tarefa (PUT/PATCH). O **técnico atribuído** só pode alterar o `estado` "
            "para `em_progresso` ou `concluida`; o **admin** pode editar tudo. "
            "Fechar a tarefa (`concluida`) notifica a contraparte."
        ),
        request=TarefaEscritaSerializer,
        responses={
            200: resposta_sucesso(
                TarefaCriadaSerializer,
                "Tarefa atualizada.",
                "TarefaAtualizada",
            ),
            403: resposta_erro("Sem permissão para editar esta tarefa."),
            404: resposta_erro("Tarefa não encontrada."),
        },
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        estado_anterior = instance.estado
        if request.user.perfil == Usuario.PerfilChoices.TECNICO:
            if instance.atribuido_a_id != request.user.id:
                self.permission_denied(request, message="Sem permissão para editar esta tarefa.")
            if any(campo not in {"estado"} for campo in request.data):
                self.permission_denied(
                    request,
                    message="Como técnico só pode alterar o estado da tarefa.",
                )
            novo_estado = request.data.get("estado")
            if novo_estado == Tarefa.EstadoChoices.CANCELADA:
                self.permission_denied(
                    request,
                    message="Apenas o admin que criou a tarefa pode cancelar.",
                )
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE:
            self.permission_denied(request, message="Sem permissão para editar tarefas.")

        novo_estado = request.data.get("estado")
        if novo_estado:
            if novo_estado == Tarefa.EstadoChoices.CONCLUIDA:
                if not instance.data_conclusao:
                    instance.data_conclusao = timezone.now()
            elif instance.data_conclusao:
                instance.data_conclusao = None

        instance._utilizador_acao = request.user
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        tarefa = serializer.save()
        return resposta_view(
            data={
                "id": str(tarefa.id),
                "numero": tarefa.numero,
                "estado": tarefa.estado,
                "data_conclusao": tarefa.data_conclusao,
            }
        )

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @extend_schema(
        summary="Eliminar tarefa",
        operation_id="tarefas_eliminar",
        description="Elimina (soft delete) uma tarefa. **Apenas administradores.**",
        responses={
            200: resposta_eliminar("Tarefa eliminada.", "Tarefa"),
            403: resposta_erro("Apenas administradores podem eliminar tarefas."),
        },
    )
    def destroy(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem eliminar tarefas.")
        tarefa = self.get_object()
        tarefa.delete()
        return resposta_view(message="Tarefa eliminada com sucesso.")

    @extend_schema(
        summary="Atribuir tarefa",
        operation_id="tarefas_atribuir",
        description=(
            "Atribui a tarefa a um admin/técnico activo. **Apenas administradores.** "
            "O novo responsável é notificado (app + WhatsApp) com os detalhes da tarefa."
        ),
        request=AtribuirTarefaSerializer,
        responses={
            200: resposta_sucesso(
                AtribuirRespostaSerializer,
                "Tarefa atribuída.",
                "TarefaAtribuida",
            ),
            403: resposta_erro("Apenas administradores podem atribuir tarefas."),
            400: resposta_erro("Destinatário inválido."),
        },
    )
    @action(detail=True, methods=["post"], url_path="atribuir")
    def atribuir(self, request, pk=None):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem atribuir tarefas.")
        instance = self.get_object()
        serializer = AtribuirTarefaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        destino = serializer.validated_data["atribuido_a_id"]
        instance.atribuido_a = destino
        instance._utilizador_acao = request.user
        instance.save(update_fields=["atribuido_a", "data_actualizacao"])
        return resposta_view(
            data={
                "id": str(instance.id),
                "atribuido_a_id": str(destino.id),
                "atribuido_a_nome": destino.nome,
            }
        )

    @extend_schema(
        summary="Concluir tarefa",
        operation_id="tarefas_concluir",
        description=(
            "Marca a tarefa como `concluida`. Pode ser feito pelo **técnico atribuído** ou pelo "
            "**admin que criou a tarefa**. Gera notificação (app + WhatsApp) à contraparte."
        ),
        responses={
            200: resposta_sucesso(
                TarefaCriadaSerializer,
                "Tarefa concluída.",
                "TarefaConcluida",
            ),
            403: resposta_erro("Apenas o técnico atribuído ou o admin que criou pode concluir."),
        },
    )
    @action(detail=True, methods=["post"], url_path="concluir")
    def concluir(self, request, pk=None):
        instance = self.get_object()
        pode_tecnico = (
            request.user.perfil == Usuario.PerfilChoices.TECNICO
            and instance.atribuido_a_id == request.user.id
        )
        pode_admin = (
            request.user.perfil == Usuario.PerfilChoices.ADMIN
            and instance.criado_por_id == request.user.id
        )
        if not (pode_tecnico or pode_admin):
            self.permission_denied(
                request,
                message="Apenas o técnico atribuído ou o admin que criou pode concluir.",
            )
        instance.estado = Tarefa.EstadoChoices.CONCLUIDA
        if not instance.data_conclusao:
            instance.data_conclusao = timezone.now()
        instance._utilizador_acao = request.user
        instance.save(update_fields=["estado", "data_conclusao", "data_actualizacao"])
        return resposta_view(
            data={
                "id": str(instance.id),
                "estado": instance.estado,
                "data_conclusao": instance.data_conclusao,
            }
        )

    @extend_schema(
        summary="Cancelar tarefa",
        operation_id="tarefas_cancelar",
        description=(
            "Cancela a tarefa (`cancelada`). **Apenas o admin que criou a tarefa.** "
            "O técnico atribuído é notificado (app + WhatsApp)."
        ),
        responses={
            200: resposta_sucesso(
                TarefaCriadaSerializer,
                "Tarefa cancelada.",
                "TarefaCancelada",
            ),
            403: resposta_erro("Apenas o admin que criou a tarefa pode cancelá-la."),
        },
    )
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        instance = self.get_object()
        if request.user.perfil != Usuario.PerfilChoices.ADMIN or instance.criado_por_id != request.user.id:
            self.permission_denied(
                request,
                message="Apenas o admin que criou a tarefa pode cancelá-la.",
            )
        instance.estado = Tarefa.EstadoChoices.CANCELADA
        instance.data_conclusao = None
        instance._utilizador_acao = request.user
        instance.save(update_fields=["estado", "data_conclusao", "data_actualizacao"])
        return resposta_view(data={"id": str(instance.id), "estado": instance.estado})

    @extend_schema(
        summary="Listar e adicionar comentários",
        operation_id="tarefas_comentarios",
        description=(
            "`GET` lista os comentários da tarefa; `POST` adiciona um comentário. "
            "Ao comentar, a contraparte (técnico atribuído ou admin criador) é notificada (app + WhatsApp)."
        ),
        request=AdicionarComentarioSerializer,
        responses={
            200: resposta_sucesso(
                ComentarioResumoSerializer(many=True),
                "Lista de comentários.",
                "Comentarios",
            ),
            201: resposta_criar(
                ComentarioResumoSerializer,
                "Comentário adicionado.",
                "Comentario",
            ),
            403: resposta_erro("Sem permissão nesta tarefa."),
        },
    )
    @action(detail=True, methods=["get", "post"], url_path="comentarios")
    def comentarios(self, request, pk=None):
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and instance.atribuido_a_id != request.user.id:
            self.permission_denied(request, message="Sem permissão nesta tarefa.")

        if request.method == "GET":
            serializer = ComentarioTarefaSerializer(instance.comentarios.all(), many=True)
            return resposta_view(data=serializer.data)

        serializer = AdicionarComentarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comentario = ComentarioTarefa.objects.create(
            tarefa=instance,
            utilizador=request.user,
            texto=serializer.validated_data["texto"],
        )
        return resposta_view(
            data={
                "id": str(comentario.id),
                "tarefa_id": str(instance.id),
                "utilizador_nome": request.user.nome,
                "texto": comentario.texto,
                "data_criacao": comentario.data_criacao,
            },
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Anexar ficheiros",
        operation_id="tarefas_anexos",
        description=(
            "Anexa um ou mais ficheiros (`ficheiro`) à tarefa, com `descricao` opcional. "
            "O técnico atribuído pode anexar ficheiros à própria tarefa."
        ),
        request={"multipart/form-data": CarregarAnexoSerializer},
        responses={
            201: resposta_criar(
                AnexoResumoSerializer(many=True),
                "Ficheiros anexados.",
                "Anexos",
            ),
            403: resposta_erro("Sem permissão para anexar ficheiros."),
        },
    )
    @action(detail=True, methods=["post"], url_path="anexos", parser_classes=[parsers.MultiPartParser])
    def anexos(self, request, pk=None):
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and instance.atribuido_a_id != request.user.id:
            self.permission_denied(request, message="Sem permissão para anexar ficheiros.")

        arquivos = request.FILES.getlist("ficheiro")
        anexos = []
        for arquivo in arquivos:
            anexo = AnexoTarefa.objects.create(
                tarefa=instance,
                utilizador=request.user,
                arquivo=arquivo,
                descricao=request.data.get("descricao", ""),
            )
            anexos.append({
                "id": str(anexo.id),
                "arquivo": anexo.arquivo.url,
                "nome": anexo.arquivo.name,
            })
        return resposta_view(data=anexos, status_code=status.HTTP_201_CREATED)