from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def manipulador_excecao_personalizado(exc, context):
    resposta = exception_handler(exc, context)
    if resposta is None:
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

    resposta.data = {
        "success": False,
        "error": {
            "code": codigo,
            "message": mensagem,
            "details": detalhes,
        },
    }
    return resposta
