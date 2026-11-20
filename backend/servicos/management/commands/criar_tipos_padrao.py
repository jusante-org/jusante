"""Cria os tipos de OS iniciais para um município.

Uso: python manage.py criar_tipos_padrao 3550308
"""
from django.core.management.base import BaseCommand, CommandError

from nucleo.models import Municipio
from servicos.models import Prioridade, Sistema, TipoOS

TIPOS_PADRAO = [
    # nome, sistema, prioridade padrão, costuma gerar reposição, é o tipo de reposição
    ("Vazamento na rede", Sistema.AGUA, Prioridade.ALTA, True, False),
    ("Vazamento no ramal / cavalete", Sistema.AGUA, Prioridade.ALTA, True, False),
    ("Falta d'água", Sistema.AGUA, Prioridade.ALTA, False, False),
    ("Ligação nova de água", Sistema.AGUA, Prioridade.NORMAL, True, False),
    ("Corte / religação", Sistema.AGUA, Prioridade.NORMAL, False, False),
    ("Troca de hidrômetro", Sistema.AGUA, Prioridade.BAIXA, False, False),
    ("Desobstrução de rede ou ramal de esgoto", Sistema.ESGOTO, Prioridade.ALTA, True, False),
    ("Extravasamento de PV / esgoto a céu aberto", Sistema.ESGOTO, Prioridade.ALTA, True, False),
    ("Ligação nova de esgoto", Sistema.ESGOTO, Prioridade.NORMAL, True, False),
    ("Reposição de pavimento / calçada", Sistema.APOIO, Prioridade.NORMAL, False, True),
]


class Command(BaseCommand):
    help = "Cria os tipos de OS iniciais para o município informado pelo código IBGE."

    def add_arguments(self, parser):
        parser.add_argument("codigo_ibge")

    def handle(self, *args, codigo_ibge, **opcoes):
        try:
            municipio = Municipio.objects.get(codigo_ibge=codigo_ibge)
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {codigo_ibge} não cadastrado.") from exc

        criados = 0
        for nome, sistema, prioridade, gera, e_rep in TIPOS_PADRAO:
            _, novo = TipoOS.objects.get_or_create(
                municipio=municipio, nome=nome,
                defaults={"sistema": sistema, "prioridade_padrao": prioridade,
                          "gera_reposicao": gera, "e_reposicao": e_rep},
            )
            criados += novo
        self.stdout.write(self.style.SUCCESS(f"{criados} tipo(s) criado(s) para {municipio}."))
