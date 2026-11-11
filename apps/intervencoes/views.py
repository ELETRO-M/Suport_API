from datetime import timedelta
from typing import cast


from django.db.models import Q
from django.utils import timezone
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema
from apps.usuarios.models import Usuario
from apps.configuracoes.responses import resposta_sucesso, resposta_erro
from apps.intervencoes.models import (
    AnexoIntervencao,
    ComentarioIntervencao,
    HoraTrabalho,
    Intervencao,
    HistoricoEstadoIntervencao,
    SolicitacaoIntervencao
)
from apps.intervencoes.serializers import (
    AdicionarComentarioSerializer,
    AtribuirTecnicoSerializer,
    CarregarAnexoSerializer,
    CriarSolicitacaoSerializer,
    SolicitacaoIntervencaoSerializer,
    TecnicoRelatorioAtualizacaoSerializer,
    TecnicoRelatorioEscritaSerializer,
    TecnicoRelatorioListaSerializer,
    IntervencaoAtualizacaoSerializer,
    IntervencaoDetalheSerializer,
    IntervencaoEscritaSerializer,
    IntervencaoListaSerializer,
    HistoricoEstadoIntervencaoSerializer
)
from apps.notificacoes.models import Notificacao

@extend_schema(tags=["Intervenções"])
class IntervencaoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]
    ordering_fields = ("data_abertura", "data_conclusao")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Intervencao.objects.none()
        request = cast(Request, self.request)
        queryset = Intervencao.objects.select_related("cliente", "tecnico", "contrato").prefetch_related(
            "historico_status",
            "comentarios",
            "anexos",
        )
        params = request.query_params
        if params.get("cliente_id"):
            queryset = queryset.filter(cliente_id=params["cliente_id"])
        if params.get("tecnico_id"):
            queryset = queryset.filter(tecnico_id=params["tecnico_id"])
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        if params.get("prioridade"):
            queryset = queryset.filter(prioridade=params["prioridade"])
        if params.get("data_inicio"):
            queryset = queryset.filter(data_abertura__date__gte=params["data_inicio"])
        if params.get("data_fim"):
            queryset = queryset.filter(data_abertura__date__lte=params["data_fim"])

        utilizador = request.user
        if params.get("modo_atribuicao"):
            queryset = queryset.filter(modo_atribuicao=params["modo_atribuicao"])
        if utilizador.perfil == Usuario.PerfilChoices.TECNICO:
            # O técnico vê as intervenções da equipa (para poder pedir intervenção
            # nos tickets de outro colega). Só pode escrever nos que lhe são atribuídos.
            # ?apenas_minhas=true restringe às suas + às de broadcast sem responsável.
            if str(params.get("apenas_minhas", "")).lower() in {"1", "true", "sim"}:
                queryset = queryset.filter(
                    Q(tecnico=utilizador) | Q(modo_atribuicao="broadcast", tecnico__isnull=True)
                )
        elif utilizador.perfil == Usuario.PerfilChoices.CLIENTE:
            queryset = queryset.filter(cliente=utilizador)
        return queryset.order_by("-data_abertura")

    serializer_action_classes = {
        "retrieve": IntervencaoDetalheSerializer,
        "create": IntervencaoEscritaSerializer,
        "update": IntervencaoAtualizacaoSerializer,
        "partial_update": IntervencaoAtualizacaoSerializer,
        "atribuir": AtribuirTecnicoSerializer,
        "comentarios": AdicionarComentarioSerializer,
        "anexos": CarregarAnexoSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_action_classes.get(
            self.action,
            IntervencaoListaSerializer
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return resposta_sucesso(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, context={"request": request})
        return resposta_sucesso(data=serializer.data)

    @extend_schema(request={"multipart/form-data": IntervencaoEscritaSerializer})
    def create(self, request, *args, **kwargs):
        if request.user.perfil not in {Usuario.PerfilChoices.ADMIN, Usuario.PerfilChoices.CLIENTE}:
            self.permission_denied(request, message="Sem permissão para criar intervenções.")
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
       
        return resposta_sucesso(
            data={"id": str(obj.id), "numero": obj.numero, "status": obj.status},
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        if request.user.perfil != Usuario.PerfilChoices.ADMIN and not(request.user.perfil == Usuario.PerfilChoices.TECNICO and instance.tecnico_id == request.user.id):
            self.permission_denied(request, message="Apenas o técnico atribuído pode actualizar.")
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE:
            self.permission_denied(request, message="Clientes não podem actualizar intervenções.")
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(data={"id": str(obj.id), "status": obj.status})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        pode_apagar = (
            request.user.perfil == Usuario.PerfilChoices.ADMIN
            or (
                request.user.perfil == Usuario.PerfilChoices.CLIENTE
                and instance.cliente_id == request.user.id
            )
        )
        if not pode_apagar:
            self.permission_denied(
                request,
                message="Apenas administradores ou o cliente que criou a intervenção podem deletar.",
            )
        instance.delete()
        return resposta_sucesso(message="Intervenção deletada com sucesso")
        '''
    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        intervencao = self.get_object()

        try:
            html_string = render_to_string(
                "contrato.html",
                {"intervencao": intervencao}
            )

            pdf = HTML(string=html_string).write_pdf()

            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="intervencao_{intervencao.pk}.pdf"'

            return response

        except Exception as e:
            logger.exception(e)
            return HttpResponse(str(e), status=500)
            '''

    

    @action(detail=True, methods=["post"], url_path="atribuir")
    def atribuir(self, request, pk=None):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem atribuir técnicos.")
        instance = self.get_object()
        serializer = AtribuirTecnicoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tecnico = serializer.validated_data["tecnico_id"]
        instance.tecnico = tecnico
        instance.save(update_fields=["tecnico"])
    
        Notificacao.objects.create(
            utilizador=tecnico,
            titulo=f"Nova intervenção na empresa {instance.cliente.empresa.nome}",
            mensagem=(
                f"Foi-lhe atribuída uma nova intervenção.\n"
                f"- Número: {instance.numero}\n"
                f"- Título: {instance.titulo}\n"
                f"- Prioridade: {instance.prioridade}\n"
                f"- Tipo de actuação: {instance.actuacao_tipo}\n"
                f"- Cliente: {instance.cliente.nome} / Empresa: {instance.cliente.empresa.nome}"
            ),
            tipo="informação",
            link=f"/intervencoes/{instance.id}",
        )

        return resposta_sucesso(
            data={"id": str(instance.id), "tecnico_id": str(tecnico.id), "tecnico_nome": tecnico.nome}
        )

    @action(detail=True, methods=["post"], url_path="assumir")
    def assumir(self, request, pk=None):
        if request.user.perfil != Usuario.PerfilChoices.TECNICO:
            self.permission_denied(request, message="Apenas técnicos podem assumir intervenções.")
        instance = self.get_object()
        if instance.modo_atribuicao != "broadcast" or instance.tecnico_id:
            return resposta_sucesso(data={"id": str(instance.id), "tecnico_id": str(instance.tecnico_id or "")})
        instance.tecnico = request.user
        instance.save(update_fields=["tecnico"])
        return resposta_sucesso(data={"id": str(instance.id), "tecnico_id": str(request.user.id), "tecnico_nome": request.user.nome})

    @action(detail=True, methods=["post"], url_path="comentarios")
    def comentarios(self, request, pk=None):
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO:
            # O chat interno (apchat) só para técnicos autorizados pelo administrador.
            if not request.user.acesso_apchat:
                self.permission_denied(request, message="Sem acesso autorizado ao chat interno.")
            # Só o técnico atribuído pode intervir; os restantes apenas leem.
            if instance.tecnico_id != request.user.id:
                self.permission_denied(request, message="Sem permissão para comentar esta intervenção.")
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE and instance.cliente_id != request.user.id:
            self.permission_denied(request, message="Sem permissão para comentar esta intervenção.")
        serializer = AdicionarComentarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comentario = ComentarioIntervencao.objects.create(
            intervencao=instance,
            usuario=request.user,
            **serializer.validated_data,
        )
        utilizador_destino = instance.cliente if request.user.perfil == Usuario.PerfilChoices.TECNICO else instance.tecnico
        if utilizador_destino:
            Notificacao.objects.create(
                utilizador=utilizador_destino,
                tipo="comentario_adicionado",
                titulo="Novo comentário",
                mensagem=f"Foi adicionado um comentário na intervenção {instance.numero}.",
                link=f"/intervencoes/{instance.id}",
            )
        return resposta_sucesso(
            data={
                "id": str(comentario.id),
                "intervencao_id": str(instance.id),
                "usuario_nome": request.user.nome,
                "texto": comentario.texto,
                "data_criacao": comentario.data_criacao,
            },
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(request={"multipart/form-data": CarregarAnexoSerializer})
    @action(detail=True, methods=["post"], url_path="anexos", parser_classes=[parsers.MultiPartParser])
    def anexos(self, request, pk=None):
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO:
            if not request.user.acesso_apchat:
                self.permission_denied(request, message="Sem acesso autorizado ao chat interno.")
            if instance.tecnico_id != request.user.id:
                self.permission_denied(request, message="Sem permissão para anexar ficheiros.")
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE and instance.cliente_id != request.user.id:
            self.permission_denied(request, message="Sem permissão para anexar ficheiros.")
    

        instance = self.get_object()

        arquivos = request.FILES.getlist("ficheiro")

        anexos = []

        for arquivo in arquivos:

            anexo = AnexoIntervencao.objects.create(
                intervencao=instance,
                utilizador=request.user,
                arquivo=arquivo,
                descricao=request.data.get("descricao", "")
            )

            anexos.append({
                "id": str(anexo.id),
                "arquivo": anexo.url_para(request.user),
                "nome": anexo.arquivo.name,
            })

        return resposta_sucesso(
            data=anexos,
            status_code=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"anexos/(?P<anexo_id>[^/.]+)/transcrever",
    )
    def transcrever_anexo(self, request, pk=None, anexo_id=None):
        """Transcreve uma nota de voz com Whisper local (faster-whisper)."""
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and instance.tecnico_id != request.user.id:
            self.permission_denied(request, message="Sem permissão para transcrever este áudio.")
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE and instance.cliente_id != request.user.id:
            self.permission_denied(request, message="Sem permissão para transcrever este áudio.")

        anexo = instance.anexos.filter(id=anexo_id).first()
        if not anexo:
            return resposta_erro(
                code="NOT_FOUND",
                message="Anexo não encontrado.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if anexo.transcricao:
            return resposta_sucesso(
                data={
                    "anexo_id": str(anexo.id),
                    "texto": anexo.transcricao,
                    "idioma": anexo.idioma_transcricao,
                    "cache": True,
                }
            )

        from apps.intervencoes.transcricao import transcrever_url

        try:
            url = anexo.url_para(request.user)
            texto, idioma = transcrever_url(url, request.data.get("idioma") or None)
        except Exception as exc:  # noqa: BLE001 - devolve erro legível ao frontend
            return resposta_erro(
                code="TRANSCRICAO_FALHOU",
                message=f"Não foi possível transcrever o áudio: {exc}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        if not texto:
            return resposta_erro(
                code="SEM_FALA",
                message="Não foi detetada fala no áudio.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        anexo.transcricao = texto
        anexo.idioma_transcricao = idioma or ""
        anexo.save(update_fields=["transcricao", "idioma_transcricao"])

        return resposta_sucesso(
            data={
                "anexo_id": str(anexo.id),
                "texto": texto,
                "idioma": idioma,
                "cache": False,
            }
        )


@extend_schema(tags=["Solicitações de intervenção"])
class SolicitacaoIntervencaoViewSet(viewsets.ModelViewSet):
    """Pedidos para intervir numa intervenção.

    - O técnico pede para intervir num ticket que não lhe está atribuído.
    - O administrador aprova (o ticket passa para o técnico que pediu)
      ou rejeita com justificação.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = SolicitacaoIntervencaoSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SolicitacaoIntervencao.objects.none()
        request = cast(Request, self.request)
        queryset = SolicitacaoIntervencao.objects.select_related(
            "intervencao", "intervencao__cliente", "intervencao__tecnico", "utilizador"
        )
        estado = request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        if request.user.perfil == Usuario.PerfilChoices.ADMIN:
            return queryset
        # Só vê os próprios pedidos.
        return queryset.filter(utilizador=request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return resposta_sucesso(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = CriarSolicitacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        intervencao = Intervencao.objects.filter(id=dados["intervencao_id"]).first()
        if not intervencao:
            return resposta_erro(
                code="NOT_FOUND", message="Intervenção não encontrada.", status_code=404
            )

        utilizador = request.user
        if utilizador.perfil == Usuario.PerfilChoices.CLIENTE:
            if intervencao.cliente_id != utilizador.id:
                return resposta_erro(
                    code="FORBIDDEN",
                    message="Só pode pedir intervenção nos seus atendimentos.",
                    status_code=403,
                )
        elif utilizador.perfil != Usuario.PerfilChoices.TECNICO:
            return resposta_erro(
                code="FORBIDDEN",
                message="Pedidos de intervenção só de técnicos ou clientes.",
                status_code=403,
            )

        if (
            utilizador.perfil == Usuario.PerfilChoices.TECNICO
            and intervencao.tecnico_id == utilizador.id
        ):
            return resposta_erro(
                code="JA_RESPONSAVEL",
                message="Já é o técnico responsável por esta intervenção.",
                status_code=400,
            )

        ja_existe = SolicitacaoIntervencao.objects.filter(
            intervencao=intervencao,
            utilizador=utilizador,
            estado=SolicitacaoIntervencao.EstadoChoices.PENDENTE,
        ).first()
        if ja_existe:
            return resposta_erro(
                code="JA_PENDENTE",
                message="Já tem um pedido pendente nesta intervenção.",
                status_code=400,
            )

        solicitacao = SolicitacaoIntervencao.objects.create(
            intervencao=intervencao,
            utilizador=utilizador,
            tipo=dados.get("tipo") or SolicitacaoIntervencao.TipoChoices.INTERVENCAO,
            justificativa=dados.get("justificativa", ""),
        )

        # Avisa os administradores.
        for admin in Usuario.objects.filter(perfil=Usuario.PerfilChoices.ADMIN):
            Notificacao.objects.create(
                utilizador=admin,
                tipo="solicitacao_intervencao",
                titulo="Pedido de intervenção",
                mensagem=(
                    f"{utilizador.nome} pediu para intervir na intervenção "
                    f"{intervencao.numero} — {intervencao.titulo}."
                ),
                link=f"/intervencoes/{intervencao.id}",
            )

        return resposta_sucesso(
            data=SolicitacaoIntervencaoSerializer(solicitacao).data,
            status_code=status.HTTP_201_CREATED,
        )

    def _responder(self, request, aprovado: bool):
        solicitacao = self.get_object()
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem responder.")

        if solicitacao.estado != SolicitacaoIntervencao.EstadoChoices.PENDENTE:
            return resposta_erro(
                code="JA_RESPONDIDO",
                message="Este pedido já foi respondido.",
                status_code=400,
            )

        solicitacao.estado = (
            SolicitacaoIntervencao.EstadoChoices.APROVADO
            if aprovado
            else SolicitacaoIntervencao.EstadoChoices.REJEITADO
        )
        solicitacao.respondido_por = request.user
        solicitacao.data_resposta = timezone.now()
        solicitacao.motivo = (request.data.get("motivo") or "")[:255]
        solicitacao.save(
            update_fields=["estado", "respondido_por", "data_resposta", "motivo"]
        )

        # Ao aprovar, o pedido passa a ser do técnico que pediu.
        if aprovado and solicitacao.utilizador.perfil == Usuario.PerfilChoices.TECNICO:
            intervencao = solicitacao.intervencao
            if intervencao.tecnico_id != solicitacao.utilizador_id:
                anterior = intervencao.tecnico
                intervencao.tecnico = solicitacao.utilizador
                intervencao.save(update_fields=["tecnico"])
                if anterior:
                    Notificacao.objects.create(
                        utilizador=anterior,
                        tipo="intervencao_reatribuida",
                        titulo="Intervenção reatribuída",
                        mensagem=(
                            f"A intervenção {intervencao.numero} passou para "
                            f"{solicitacao.utilizador.nome}."
                        ),
                        link=f"/intervencoes/{intervencao.id}",
                    )

        Notificacao.objects.create(
            utilizador=solicitacao.utilizador,
            tipo="solicitacao_respondida",
            titulo="Pedido de intervenção respondido",
            mensagem=(
                f"O seu pedido para intervir na intervenção "
                f"{solicitacao.intervencao.numero} foi "
                f"{'aprovado' if aprovado else 'rejeitado'}."
                + (f" Motivo: {solicitacao.motivo}" if solicitacao.motivo else "")
            ),
            link=f"/intervencoes/{solicitacao.intervencao_id}",
        )

        return resposta_sucesso(data=SolicitacaoIntervencaoSerializer(solicitacao).data)

    @action(detail=True, methods=["post"], url_path="aprovar")
    def aprovar(self, request, pk=None):
        return self._responder(request, aprovado=True)

    @action(detail=True, methods=["post"], url_path="rejeitar")
    def rejeitar(self, request, pk=None):
        return self._responder(request, aprovado=False)


@extend_schema(tags=["Relatórios Técnicos"])
class HoraTrabalhoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return HoraTrabalho.objects.none()
        request = cast(Request, self.request)
        queryset = HoraTrabalho.objects.select_related("intervencao", "tecnico")
        params = request.query_params
        if params.get("intervencao_id"):
            queryset = queryset.filter(intervencao_id=params["intervencao_id"])
        if params.get("tecnico_id"):
            queryset = queryset.filter(tecnico_id=params["tecnico_id"])
        if params.get("data_inicio"):
            queryset = queryset.filter(data_trabalho__gte=params["data_inicio"])
        if params.get("data_fim"):
            queryset = queryset.filter(data_trabalho__lte=params["data_fim"])
        if request.user.perfil == Usuario.PerfilChoices.TECNICO:
            queryset = queryset.filter(tecnico=request.user)
        return queryset.order_by("-data_trabalho", "-data_criacao")

    def get_serializer_class(self):
        if self.action == "create":
            return TecnicoRelatorioEscritaSerializer
        if self.action in {"update", "partial_update"}:
            return TecnicoRelatorioAtualizacaoSerializer
        return TecnicoRelatorioListaSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return resposta_sucesso(data=serializer.data)

    def create(self, request, *args, **kwargs):
        if request.user.perfil not in {Usuario.PerfilChoices.ADMIN, Usuario.PerfilChoices.TECNICO}:
            self.permission_denied(request, message="Sem permissão para registar relatório.")
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(
            data={
                "id": str(obj.id),
                "intervencao_id": str(obj.intervencao_id),
                "tecnico_id": str(obj.tecnico_id),
                "horas": obj.horas,
                "data_trabalho": obj.data_trabalho,
            },
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and instance.tecnico_id != request.user.id:
            self.permission_denied(request, message="So pode actualizar as proprias horas.")
        serializer = self.get_serializer(instance, data=request.data, partial=False, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(data={"id": str(obj.id), "horas": obj.horas})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.perfil not in {Usuario.PerfilChoices.TECNICO, Usuario.PerfilChoices.ADMIN}:
            self.permission_denied(request, message="Sem permissão para apagar.")
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and instance.tecnico_id != request.user.id:
            self.permission_denied(request, message="So pode apagar as proprias horas.")
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and timezone.now() - instance.data_criacao > timedelta(hours=24):
            self.permission_denied(request, message="So pode apagar registos nas primeiras 24 horas.")
        instance.delete()
        return resposta_sucesso(message="Registo deletado com sucesso")


TecnicoRelatorioViewSet = HoraTrabalhoViewSet

@extend_schema(tags=["Intervenções"])
class HistoricoViewSet(viewsets.ReadOnlyModelViewSet):

    permission_classes = [IsAuthenticated]

    serializer_class = HistoricoEstadoIntervencaoSerializer
    queryset = HistoricoEstadoIntervencao.objects.all()
