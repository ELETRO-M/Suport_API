from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError


def manipulador_excecao_personalizado(exc, context):
    resposta = exception_handler(exc, context)

    if resposta is None:
        if isinstance(exc, DjangoValidationError):
            detalhes_django = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            resposta = Response(
                {"detail": "Ocorreu um erro de validação.", "details": detalhes_django},
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif isinstance(exc, IntegrityError):
            mensagem = str(exc).lower()
            if "duplicate" in mensagem or "unique constraint" in mensagem:
                resposta = Response(
                    {"detail": "Registo duplicado. Já existe um registo com estes dados."},
                    status=status.HTTP_409_CONFLICT,
                )
            else:
                resposta = Response(
                    {"detail": "Erro de integridade da base de dados."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return resposta

    codigo = "ERROR"
    if resposta.status_code == status.HTTP_401_UNAUTHORIZED:
        codigo = "AUTH_001"
    elif resposta.status_code == status.HTTP_403_FORBIDDEN:
        codigo = "AUTH_003"
    elif resposta.status_code == status.HTTP_404_NOT_FOUND:
        codigo = "RES_001"
    elif resposta.status_code == status.HTTP_409_CONFLICT:
        codigo = "RES_002"
    elif resposta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        codigo = "VAL_001"
    elif resposta.status_code == status.HTTP_400_BAD_REQUEST or isinstance(exc, ValidationError):
        codigo = "VAL_001"

    mensagem = "Ocorreu um erro ao processar a requisição."
    detalhes = resposta.data
    if isinstance(resposta.data, dict):
        mensagem = resposta.data.get("detail") or resposta.data.get("non_field_errors", [mensagem])[0]

    if isinstance(exc, DjangoValidationError) and "detalhes_django" in locals():
        detalhes = detalhes_django
    elif isinstance(exc, IntegrityError):
        detalhes = None

    resposta.data = {
        "success": False,
        "error": {
            "code": codigo,
            "message": mensagem,
            "details": detalhes,
        },
    }
    return resposta
