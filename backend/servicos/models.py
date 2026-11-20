"""Modelos do módulo de Ordens de Serviço (MVP).

Referência: docs/mvp-ordens-de-servico.md

Regra central: o status de uma OS só muda pelas funções de `servicos.fluxo`, que validam
a transição, verificam o perfil de quem age e registram um `EventoOS` imutável.
"""
from django.conf import settings
from django.contrib.gis.db import models
from django.db import transaction
from django.utils import timezone

from nucleo.models import Equipe, Municipio


class Sistema(models.TextChoices):
    AGUA = "agua", "Água"
    ESGOTO = "esgoto", "Esgoto"
    APOIO = "apoio", "Apoio"


class Prioridade(models.TextChoices):
    BAIXA = "baixa", "Baixa"
    NORMAL = "normal", "Normal"
    ALTA = "alta", "Alta"
    EMERGENCIA = "emergencia", "Emergência"


class TipoOS(models.Model):
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, related_name="tipos_os")
    nome = models.CharField(max_length=120)
    sistema = models.CharField(max_length=10, choices=Sistema.choices)
    prioridade_padrao = models.CharField(max_length=12, choices=Prioridade.choices, default=Prioridade.NORMAL)
    gera_reposicao = models.BooleanField(
        "costuma gerar reposição", default=False,
        help_text="Apenas indicativo; quem decide em campo é a equipe.",
    )
    e_reposicao = models.BooleanField(
        "é o tipo de reposição de pavimento", default=False,
        help_text="Tipo usado nas OS filhas criadas automaticamente após o reparo.",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "tipo de OS"
        verbose_name_plural = "tipos de OS"
        ordering = ["sistema", "nome"]
        constraints = [
            models.UniqueConstraint(fields=["municipio", "nome"], name="tipo_os_nome_unico_por_municipio"),
            models.UniqueConstraint(
                fields=["municipio"], condition=models.Q(e_reposicao=True),
                name="um_tipo_de_reposicao_por_municipio",
            ),
        ]

    def __str__(self):
        return self.nome


class Solicitante(models.Model):
    """Quem pediu o serviço. Coletar o mínimo necessário (LGPD)."""

    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, related_name="solicitantes")
    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=20, blank=True)
    endereco = models.CharField("endereço", max_length=255, blank=True)

    class Meta:
        verbose_name = "solicitante"

    def __str__(self):
        return self.nome


class Status(models.TextChoices):
    ABERTA = "aberta", "Aberta"
    TRIADA = "triada", "Triada"
    PROGRAMADA = "programada", "Programada"
    EM_EXECUCAO = "em_execucao", "Em execução"
    EXECUTADA = "executada", "Executada"
    AGUARDANDO_REPOSICAO = "aguardando_reposicao", "Aguardando reposição"
    ENCERRADA = "encerrada", "Encerrada"
    CANCELADA = "cancelada", "Cancelada"


class TipoPavimento(models.TextChoices):
    ASFALTO = "asfalto", "Asfalto"
    PARALELEPIPEDO = "paralelepipedo", "Paralelepípedo / bloquete"
    CONCRETO = "concreto", "Concreto"
    CALCADA = "calcada", "Calçada"
    TERRA = "terra", "Terra / sem pavimento"


class SequenciaOS(models.Model):
    """Contador de numeração das OS por município e ano (ex.: 2026-000123)."""

    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    ano = models.PositiveSmallIntegerField()
    ultimo = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["municipio", "ano"], name="sequencia_unica")]

    @classmethod
    def proximo_numero(cls, municipio: Municipio) -> str:
        ano = timezone.localdate().year
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(municipio=municipio, ano=ano)
            seq.ultimo += 1
            seq.save(update_fields=["ultimo"])
        return f"{ano}-{seq.ultimo:06d}"


class OrdemServico(models.Model):
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, related_name="ordens_servico")
    numero = models.CharField("número", max_length=12, editable=False)
    tipo = models.ForeignKey(TipoOS, on_delete=models.PROTECT, related_name="ordens_servico")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ABERTA, editable=False)
    prioridade = models.CharField(max_length=12, choices=Prioridade.choices, default=Prioridade.NORMAL)

    # Pedido
    solicitante = models.ForeignKey(
        Solicitante, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordens_servico"
    )
    endereco = models.CharField("endereço", max_length=255)
    referencia = models.CharField("ponto de referência", max_length=255, blank=True)
    descricao = models.TextField("descrição do pedido")
    ponto_informado = models.PointField(
        "local informado", srid=4326, null=True, blank=True,
        help_text="Onde o atendente marcou no mapa ao abrir a OS.",
    )

    # Triagem e programação
    equipe = models.ForeignKey(
        Equipe, on_delete=models.PROTECT, null=True, blank=True, related_name="ordens_servico"
    )
    data_programada = models.DateField("data programada", null=True, blank=True)

    # Execução em campo
    ponto_real = models.PointField(
        "local real do serviço", srid=4326, null=True, blank=True,
        help_text="Registrado pela equipe em campo (GPS + ajuste no mapa).",
    )
    encontrado = models.CharField("o que foi encontrado", max_length=120, blank=True)
    executado = models.CharField("o que foi feito", max_length=120, blank=True)
    observacao_campo = models.TextField("observação de campo", blank=True)
    precisa_reposicao = models.BooleanField("precisa de reposição", null=True, blank=True)
    reposicao_tipo = models.CharField(max_length=20, choices=TipoPavimento.choices, blank=True)
    reposicao_area_m2 = models.DecimalField(
        "área estimada de reposição (m²)", max_digits=7, decimal_places=2, null=True, blank=True
    )

    # Reposição: a OS filha aponta para a OS de origem.
    os_origem = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="reposicoes",
        verbose_name="OS de origem",
    )

    # Datas de cada etapa (preenchidas pelo fluxo)
    aberta_em = models.DateTimeField(default=timezone.now, editable=False)
    triada_em = models.DateTimeField(null=True, blank=True, editable=False)
    programada_em = models.DateTimeField(null=True, blank=True, editable=False)
    iniciada_em = models.DateTimeField(null=True, blank=True, editable=False)
    executada_em = models.DateTimeField(null=True, blank=True, editable=False)
    encerrada_em = models.DateTimeField(null=True, blank=True, editable=False)
    cancelada_em = models.DateTimeField(null=True, blank=True, editable=False)

    aberta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="os_abertas", editable=False
    )

    class Meta:
        verbose_name = "ordem de serviço"
        verbose_name_plural = "ordens de serviço"
        ordering = ["-aberta_em"]
        constraints = [
            models.UniqueConstraint(fields=["municipio", "numero"], name="numero_os_unico_por_municipio"),
        ]
        indexes = [models.Index(fields=["municipio", "status"])]

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = SequenciaOS.proximo_numero(self.municipio)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"OS {self.numero} · {self.tipo}"


class EventoOS(models.Model):
    """Histórico imutável de tudo o que aconteceu com uma OS."""

    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="eventos")
    momento = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    acao = models.CharField("ação", max_length=40)
    status_anterior = models.CharField(max_length=24, choices=Status.choices, blank=True)
    status_novo = models.CharField(max_length=24, choices=Status.choices, blank=True)
    observacao = models.TextField("observação", blank=True)

    class Meta:
        verbose_name = "evento da OS"
        verbose_name_plural = "eventos da OS"
        ordering = ["momento", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Eventos de OS são imutáveis.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Eventos de OS são imutáveis.")

    def __str__(self):
        return f"{self.os.numero} · {self.acao}"


class MomentoFoto(models.TextChoices):
    ANTES = "antes", "Antes"
    DEPOIS = "depois", "Depois"
    REPOSICAO = "reposicao", "Reposição"
    OUTRA = "outra", "Outra"


def _caminho_foto(instancia, nome_arquivo):
    os_ = instancia.os
    return f"os/{os_.municipio.codigo_ibge}/{os_.numero}/{instancia.momento}_{nome_arquivo}"


class Foto(models.Model):
    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="fotos")
    momento = models.CharField(max_length=10, choices=MomentoFoto.choices)
    arquivo = models.FileField(upload_to=_caminho_foto)
    tirada_em = models.DateTimeField(default=timezone.now)
    ponto = models.PointField(srid=4326, null=True, blank=True)
    enviada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        verbose_name = "foto"
        ordering = ["tirada_em"]

    def __str__(self):
        return f"{self.os.numero} · {self.get_momento_display()}"


class Peca(models.Model):
    """Catálogo de peças e materiais, com descrição padronizada."""

    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, related_name="pecas")
    descricao = models.CharField("descrição", max_length=150)
    unidade = models.CharField(max_length=10, default="un", help_text="un, m, kg…")
    diametro_mm = models.PositiveIntegerField("diâmetro (mm)", null=True, blank=True)
    material = models.CharField(max_length=40, blank=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "peça"
        ordering = ["descricao"]
        constraints = [
            models.UniqueConstraint(fields=["municipio", "descricao"], name="peca_unica_por_municipio"),
        ]

    def __str__(self):
        return self.descricao


class PecaUsada(models.Model):
    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="pecas_usadas")
    peca = models.ForeignKey(Peca, on_delete=models.PROTECT, related_name="usos")
    quantidade = models.DecimalField(max_digits=9, decimal_places=2)

    class Meta:
        verbose_name = "peça usada"
        verbose_name_plural = "peças usadas"

    def __str__(self):
        return f"{self.quantidade} {self.peca.unidade} · {self.peca}"


class ObservacaoRede(models.Model):
    """O que a equipe viu da rede no local do serviço. Alimenta o cadastro com o tempo."""

    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="observacoes_rede")
    sistema = models.CharField(max_length=10, choices=Sistema.choices)
    diametro_mm = models.PositiveIntegerField("diâmetro (mm)", null=True, blank=True)
    material = models.CharField(max_length=40, blank=True)
    profundidade_m = models.DecimalField("profundidade (m)", max_digits=4, decimal_places=2, null=True, blank=True)
    pavimento = models.CharField(max_length=20, choices=TipoPavimento.choices, blank=True)
    ponto = models.PointField(srid=4326, null=True, blank=True)
    revisada = models.BooleanField(
        default=False, help_text="Marcado pelo técnico depois de incorporar ao cadastro oficial."
    )
    registrada_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "observação de rede"
        verbose_name_plural = "observações de rede"

    def __str__(self):
        return f"{self.os.numero} · {self.get_sistema_display()}"
