"""Administração das Ordens de Serviço.

O painel administrativo serve para configuração (tipos, peças) e consulta. O status das OS
não é editável aqui: muda apenas pelo fluxo (servicos.fluxo), que registra o histórico.
"""
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import (
    EventoOS,
    Foto,
    ObservacaoRede,
    OrdemServico,
    Peca,
    PecaUsada,
    Solicitante,
    Status,
    TipoOS,
)


@admin.register(TipoOS)
class TipoOSAdmin(admin.ModelAdmin):
    list_display = ["nome", "municipio", "sistema", "prioridade_padrao", "gera_reposicao", "e_reposicao", "ativo"]
    list_filter = ["municipio", "sistema", "ativo"]
    search_fields = ["nome"]


@admin.register(Solicitante)
class SolicitanteAdmin(admin.ModelAdmin):
    list_display = ["nome", "telefone", "municipio"]
    list_filter = ["municipio"]
    search_fields = ["nome", "telefone"]


@admin.register(Peca)
class PecaAdmin(admin.ModelAdmin):
    list_display = ["descricao", "unidade", "diametro_mm", "material", "municipio", "ativa"]
    list_filter = ["municipio", "material", "ativa"]
    search_fields = ["descricao"]


class FotoInline(admin.TabularInline):
    model = Foto
    extra = 0
    fields = ["momento", "arquivo", "tirada_em", "enviada_por"]
    readonly_fields = ["enviada_por"]


class PecaUsadaInline(admin.TabularInline):
    model = PecaUsada
    extra = 0
    autocomplete_fields = ["peca"]


class ObservacaoRedeInline(admin.TabularInline):
    model = ObservacaoRede
    extra = 0
    fields = ["sistema", "diametro_mm", "material", "profundidade_m", "pavimento", "revisada"]


class EventoOSInline(admin.TabularInline):
    model = EventoOS
    extra = 0
    can_delete = False
    fields = ["momento", "usuario", "acao", "status_anterior", "status_novo", "observacao"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OrdemServico)
class OrdemServicoAdmin(GISModelAdmin):
    list_display = ["numero", "tipo", "status", "prioridade", "endereco", "equipe", "aberta_em"]
    list_filter = ["municipio", "status", "prioridade", "tipo__sistema", "equipe"]
    search_fields = ["numero", "endereco", "descricao", "solicitante__nome"]
    date_hierarchy = "aberta_em"
    readonly_fields = [
        "numero", "status", "aberta_por", "aberta_em", "triada_em", "programada_em",
        "iniciada_em", "executada_em", "encerrada_em", "cancelada_em", "os_origem",
    ]
    inlines = [FotoInline, PecaUsadaInline, ObservacaoRedeInline, EventoOSInline]
    fieldsets = [
        ("Identificação", {"fields": ["numero", "municipio", "tipo", "status", "prioridade", "os_origem"]}),
        ("Pedido", {"fields": ["solicitante", "endereco", "referencia", "descricao", "ponto_informado"]}),
        ("Programação", {"fields": ["equipe", "data_programada"]}),
        ("Execução em campo", {"fields": [
            "ponto_real", "encontrado", "executado", "observacao_campo",
            "precisa_reposicao", "reposicao_tipo", "reposicao_area_m2",
        ]}),
        ("Datas", {"fields": [
            "aberta_por", "aberta_em", "triada_em", "programada_em", "iniciada_em",
            "executada_em", "encerrada_em", "cancelada_em",
        ]}),
    ]

    def save_model(self, request, obj, form, change):
        novo = obj.pk is None
        if novo:
            obj.aberta_por = request.user
        super().save_model(request, obj, form, change)
        if novo:
            EventoOS.objects.create(os=obj, usuario=request.user, acao="abertura (administração)",
                                    status_novo=Status.ABERTA)

    def save_formset(self, request, form, formset, change):
        instancias = formset.save(commit=False)
        for inst in instancias:
            if isinstance(inst, Foto) and not inst.enviada_por_id:
                inst.enviada_por = request.user
            inst.save()
        for removida in formset.deleted_objects:
            removida.delete()
        formset.save_m2m()
