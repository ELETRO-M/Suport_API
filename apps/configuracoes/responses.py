from rest_framework.response import Response


def resposta_sucesso(*, data=None, message="", status_code=200, pagination=None):
    conteudo = {"success": True, "data": data}
    if message:
        conteudo["message"] = message
    if pagination is not None:
        conteudo["pagination"] = pagination
    return Response(conteudo, status=status_code)


def resposta_erro(*, code="ERROR", message="Ocorreu um erro.", details=None, status_code=400):
    conteudo = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        conteudo["error"]["details"] = details
    return Response(conteudo, status=status_code)
