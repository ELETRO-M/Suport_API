from drf_spectacular.utils import OpenApiExample, OpenApiResponse
from rest_framework import serializers


def componente_resposta_sucesso(payload, nome):
    return type(
        nome,
        (serializers.Serializer,),
        {
            "success": serializers.BooleanField(default=True),
            "data": payload,
            "message": serializers.CharField(required=False, allow_blank=True),
        },
    )


def resposta_sucesso(payload, descricao, nome, exemplos=None):
    return OpenApiResponse(
        response=componente_resposta_sucesso(payload, nome),
        description=descricao,
        examples=exemplos,
    )


def resposta_criar(payload, descricao="Recurso criado com sucesso.", nome="RespostaCriar", exemplos=None):
    return resposta_sucesso(payload, descricao, f"{nome}Criar", exemplos)


def resposta_eliminar(descricao="Recurso eliminado com sucesso.", nome="RespostaEliminar"):
    return resposta_sucesso(
        serializers.DictField(),
        descricao,
        f"{nome}Eliminar",
        exemplos=[OpenApiExample("Exemplo", value={"success": True, "message": "Recurso eliminado com sucesso."})],
    )


class RespostaErroPadrao(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    error = serializers.DictField(
        help_text="Detalhes do erro: `code` e `message` (e `details` quando aplicável)."
    )


def resposta_erro(descricao="Ocorreu um erro."):
    return OpenApiResponse(response=RespostaErroPadrao, description=descricao)