"""Núcleo comum do Jusante: municípios, usuários e equipes.

Todas as entidades dos módulos carregam o município, para que uma mesma instalação
possa atender vários municípios (por exemplo, um consórcio intermunicipal).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Municipio(models.Model):
    nome = models.CharField(max_length=120)
    uf = models.CharField("UF", max_length=2)
    codigo_ibge = models.CharField("código IBGE", max_length=7, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "município"
        ordering = ["uf", "nome"]

    def __str__(self):
        return f"{self.nome}/{self.uf}"


class Perfil(models.TextChoices):
    """Perfis de acesso. Uma pessoa pode acumular mais de um (comum em SAAEs pequenos)."""

    ATENDENTE = "atendente", "Atendente"
    ENCARREGADO = "encarregado", "Encarregado"
    CAMPO = "campo", "Equipe de campo"
    GESTOR = "gestor", "Gestor"


class Usuario(AbstractUser):
    municipio = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, null=True, blank=True, related_name="usuarios",
        help_text="Vazio apenas para administradores da instalação.",
    )
    telefone = models.CharField(max_length=20, blank=True)
    # Lista de valores de Perfil. JSON mantém a flexibilidade sem tabela extra no MVP.
    perfis = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "usuário"

    def tem_perfil(self, *perfis: str) -> bool:
        """Verdadeiro se o usuário tiver pelo menos um dos perfis informados."""
        if self.is_superuser:
            return True
        return any(p in (self.perfis or []) for p in perfis)

    def __str__(self):
        return self.get_full_name() or self.username


class Equipe(models.Model):
    class Especialidade(models.TextChoices):
        AGUA = "agua", "Água"
        ESGOTO = "esgoto", "Esgoto"
        PAVIMENTACAO = "pavimentacao", "Pavimentação"
        GERAL = "geral", "Geral"

    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, related_name="equipes")
    nome = models.CharField(max_length=80)
    especialidade = models.CharField(max_length=20, choices=Especialidade.choices, default=Especialidade.GERAL)
    membros = models.ManyToManyField(Usuario, blank=True, related_name="equipes")
    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "equipe"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(fields=["municipio", "nome"], name="equipe_nome_unico_por_municipio"),
        ]

    def __str__(self):
        return self.nome
