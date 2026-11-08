from django.contrib import admin

from apps.calendario.models import (
    CategoriaObrigacao, DocumentoObrigacao, HistoricoObrigacao,
    ObrigacaoFiscal, TarefaFiscal,
)

admin.site.register(CategoriaObrigacao)
admin.site.register(ObrigacaoFiscal)
admin.site.register(TarefaFiscal)
admin.site.register(HistoricoObrigacao)
admin.site.register(DocumentoObrigacao)
